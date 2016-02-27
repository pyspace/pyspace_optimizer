#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import shutil
import time
import warnings
from Queue import Empty
from multiprocessing import Manager

from hyperopt import STATUS_OK, tpe, STATUS_FAIL

import pySPACE
from pySPACE.missions.nodes.decorators import ChoiceParameter
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACEOptimizer.optimizer.base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.optimizer.hyperopt_optimizer.persistent_trials import MultiprocessingPersistentTrials
from pySPACEOptimizer.optimizer.optimizer_pool import OptimizerPool
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline, PipelineNode
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node
from pySPACEOptimizer.utils import OutputLogger

SENTINEL_VALUE = None


def __minimize(spec):
    pipeline, backend, base_result_dir = spec[0]
    task = pipeline.configuration
    logger = pipeline.get_logger()
    parameter_ranges = {param: [value] for param, value in spec[1].iteritems()}
    # noinspection PyBroadException
    try:
        # Execute the pipeline
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result_path = pipeline.execute(parameter_ranges=parameter_ranges,
                                           backend=backend,
                                           base_result_dir=base_result_dir)
        # Check the result
        result_file = os.path.join(result_path, "results.csv") if result_path is not None else ""
        if os.path.isfile(result_file):
            summary = PerformanceResultSummary.from_csv(result_file)
            # Calculate the mean of all data sets using the given metric
            if task["metric"] not in summary:
                raise ValueError("Metric '%s' not found in result data set" % task["metric"])

            mean = numpy.mean(numpy.asarray(summary[task["metric"]], dtype=numpy.float))

            loss = -1 * mean if "is_performance_metric" in task and task["is_performance_metric"] else mean
            logger.debug("Loss: {loss:.3f}".format(loss=loss))
            return {
                "loss": loss,
                "status": STATUS_OK
            }
        else:
            logger.debug("No results found. "
                         "Returning infinite loss and failed state")
            return {
                "loss": float("inf"),
                "status": STATUS_FAIL
            }
    except Exception:
        logger.exception("Error minimizing the pipeline:")
        return {
            "loss": float("inf"),
            "status": STATUS_FAIL
        }


def optimize_pipeline(backend, queue, pipeline):

    def _do_pass(evaluations):
        # Log errors from here with special logger
        with OutputLogger(std_out_logger=pipeline.get_logger(),
                          std_err_logger=logging.getLogger("pySPACEOptimizer.pipelines.errors")):
            for loss, parameters in trials.minimize(fn=__minimize,
                                                    space=pipeline_space,
                                                    algo=suggestion_algorithm,
                                                    max_evals=evaluations,
                                                    rseed=int(time.time())):
                # Replace indexes of choice parameters with the selected values
                new_pipeline_space = {}
                for node in pipeline.nodes:
                    new_pipeline_space.update(PipelineNode.parameter_space(node))

                for key, value in parameters.iteritems():
                    if isinstance(new_pipeline_space[key], ChoiceParameter):
                        parameters[key] = new_pipeline_space[key].choices[value]

                # And put the result into the queue
                queue.put((loss, pipeline, parameters))

    # Get the base result dir and append it to the arguments
    # Store each pipeline in it's own folder
    task = pipeline.configuration
    pipeline_hash = str(hash(pipeline)).replace("-", "_")
    base_result_dir = os.path.join(pySPACE.configuration.storage,
                                   "operation_results",
                                   "pySPACEOptimizer",
                                   pipeline_hash)
    # Create the directory if not existing
    if not os.path.isdir(base_result_dir):
        os.makedirs(base_result_dir)

    pipeline_space = [(pipeline, backend, base_result_dir), pipeline.pipeline_space]

    # Get the number of evaluations to make
    max_evaluations = task["max_evaluations"]
    suggestion_algorithm = task["suggestion_algorithm"] if task["suggestion_algorithm"] else tpe.suggest

    #  Run the minimizer using two pass evaluation
    trials = MultiprocessingPersistentTrials(trials_dir=base_result_dir)
    if "restart_evaluation" in task and task["restart_evaluation"]:
        # Delete the old values and start over again
        try:
            shutil.rmtree(base_result_dir)
            os.makedirs(base_result_dir)
            trials.delete_all()
        except OSError as exc:
            pipeline.get_logger().warning("Error while trying to remove the old data: %s", exc)

    # if max_evaluations > 1 to evaluation with two-pass
    # else do single pass evaluation
    if max_evaluations > 1:
        # first pass
        # Train with max_evaluations - 1 runs..
        _do_pass(evaluations=max_evaluations - 1)
        # second pass
        # finally evaluate with one evaluation
        _do_pass(evaluations=1)
    else:
        # simply to the evaluation
        _do_pass(evaluations=max_evaluations)


class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, task, backend, best_result_file):
        super(HyperoptOptimizer, self).__init__(task, backend, best_result_file)
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        manager = Manager()
        self._queue = manager.Queue()

    def _generate_pipelines(self):
        for pipeline in PipelineGenerator(self._task):
            self._logger.debug("Testing Pipeline: %s", pipeline)
            pipeline = Pipeline(configuration=self._task,
                                node_chain=[self._create_node(node_name) for node_name in pipeline])
            yield pipeline

    def optimize(self):
        self._logger.info("Optimizing Pipelines")
        self._logger.debug("Creating optimization pool")
        pool = OptimizerPool()

        # Enqueue the evaluations and save the results
        results = [pool.apply_async(func=optimize_pipeline, args=(self._backend, self._queue, pipeline))
                   for pipeline in self._generate_pipelines()]

        # close the pool
        pool.close()

        try:
            # Read the queue until all jobs are done or the max evaluation time is reached
            return self._read_queue(results=results)
        finally:
            pool.terminate()
            pool.join()

    def _read_queue(self, results=None):
        best = [float("inf"), None, None]
        if self._task["max_eval_time"] > 0:
            end_time = time.time() + self._task["max_eval_time"]
        else:
            end_time = float("inf")

        while time.time() < end_time:
            if self._queue.empty() and results is not None and all([result.ready() for result in results]):
                # the queue is empty and all workers are finished: break
                # but first check for errors:
                for result in results:
                    if not result.successful():
                        raise result.get()
                break
            else:
                try:
                    result = self._queue.get(timeout=1)
                    if result is SENTINEL_VALUE:
                        # SENTINEL_VALUE means no further results, break..
                        break
                    else:
                        loss, pipeline, parameters = result
                        self._logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s",
                                           pipeline, loss, parameters)
                        if loss < best[0]:
                            self._logger.info("Pipeline '%r' with parameters '%s' selected as best", pipeline,
                                              parameters)
                            best = [loss, pipeline, parameters]
                            self.store_best_result(best_pipeline=pipeline,
                                                   best_parameters=parameters)
                except Empty:
                    pass
        else:
            self._logger.info("Reached maximal evaluation time, breaking evaluation")
        return best

    def _create_node(self, node_name):
        if is_sink_node(node_name):
            return HyperoptSinkNode(node_name=node_name, task=self._task)
        elif is_source_node(node_name):
            return HyperoptSourceNode(node_name=node_name, task=self._task)
        else:
            return HyperoptNode(node_name=node_name, task=self._task)


class SerialHyperoptOptimizer(HyperoptOptimizer):
    def optimize(self):
        self._logger.info("Optimizing Pipelines")
        best = [float("inf"), None, None]
        for pipeline in self._generate_pipelines():
            optimize_pipeline(self._backend, self._queue, pipeline)
            # Append the sentinel value, because no additional result can be found
            self._queue.put(SENTINEL_VALUE)
            loss, pipeline, parameters = self._read_queue()
            self._logger.debug("Loss of Pipeline '%s' is: '%s'", pipeline, loss)
            if loss < best[0]:
                self._logger.info("Pipeline '%s' with parameters '%s' selected as best", pipeline, parameters)
                best = [loss, pipeline, parameters]
                self.store_best_result(best_pipeline=pipeline, best_parameters=parameters)
        return best
