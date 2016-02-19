#!/bin/env python
# -*- coding: utf-8 -*-
import numpy
import os
import time
import logging
import warnings

import shutil

import pySPACE

from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL

from pySPACEOptimizer.optimizer.base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.optimizer.hyperopt_optimizer.persistent_trials import MultiprocessingPersistentTrials
from pySPACEOptimizer.optimizer.optimizer_pool import OptimizerPool

from pySPACE.missions.nodes.decorators import ChoiceParameter
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline, PipelineNode
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node


def __minimize(spec):
    task, pipeline, backend, base_result_dir = spec[0]
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
                raise ValueError("Metric '%s' not found in result dataset" % task["metric"])

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


def optimize_pipeline(args):
    task, pipeline, _ = args
    # Get the base result dir and append it to the arguments
    # Store each pipeline in it's own folder
    base_result_dir = os.path.join(pySPACE.configuration.storage,
                                   "operation_results",
                                   "pySPACEOptimizer",
                                   str(hash(pipeline)))
    # Create the directory if not existing
    if not os.path.isdir(base_result_dir):
        os.makedirs(base_result_dir)

    args += (base_result_dir,)
    pipeline_space = [args, pipeline.pipeline_space]

    # Get the number of evaluations to make
    max_evals = task["max_evaluations"] if task["max_evaluations"] else 100

    #  Run the minimizer
    trials = MultiprocessingPersistentTrials(trials_dir=base_result_dir)
    if "restart_evaluation" in task and task["restart_evaluation"]:
        # Delete the old values and start over again
        try:
            shutil.rmtree(base_result_dir)
            os.makedirs(base_result_dir)
            trials.delete_all()
        except OSError as exc:
            pipeline.get_logger().warning("Error while trying to remove the old data: %s", exc)

    best = fmin(fn=__minimize,
                space=pipeline_space,
                algo=task["suggestion_algorithm"] if task["suggestion_algorithm"] else tpe.suggest,
                max_evals=max_evals,
                trials=trials,
                rseed=int(time.time()))

    # Replace indexes of choice parameters with the selected values
    new_pipeline_space = {}
    for node in pipeline.nodes:
        new_pipeline_space.update(PipelineNode.parameter_space(node))

    for key, value in best.iteritems():
        if isinstance(new_pipeline_space[key], ChoiceParameter):
            best[key] = new_pipeline_space[key].choices[value]

    # Return the best trial
    return trials.best_trial["result"]["loss"], pipeline, best


class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, task, backend, best_result_file):
        super(HyperoptOptimizer, self).__init__(task, backend, best_result_file)
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

    def _generate_pipelines(self):
        for pipeline in PipelineGenerator(self._task):
            self._logger.debug("Testing Pipeline: %s", pipeline)
            pipeline = Pipeline(configuration=self._task,
                                node_chain=[self._create_node(node_name) for node_name in pipeline])
            yield (self._task, pipeline, self._backend)
            # We need to wait at least one second before yielding the next pipeline
            # otherwise the result will be stored within the same result dir
            time.sleep(1)

    def optimize(self):
        self._logger.info("Optimizing Pipelines")
        self._logger.debug("Creating optimization pool")
        pool = OptimizerPool()
        results = pool.imap(optimize_pipeline, self._generate_pipelines())
        pool.close()

        # loss, pipeline, parameters
        best = [float("inf"), None, None]
        try:
            for loss, pipeline, parameters in results:
                self._logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s",
                                   pipeline, loss, parameters)
                if loss < best[0]:
                    self._logger.info("Pipeline '%r' with parameters '%s' selected as best", pipeline, parameters)
                    best = [loss, pipeline, parameters]
                    self.store_best_result(best_pipeline=pipeline,
                                           best_parameters=parameters)
        finally:
            pool.join()
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

        for args in self._generate_pipelines():
            loss, pipeline, parameters = optimize_pipeline(args)
            self._logger.debug("Loss of Pipeline '%s' is: '%s'", pipeline, loss)
            if loss < best[0]:
                self._logger.info("Pipeline '%s' with parameters '%s' selected as best", pipeline, parameters)
                best = [loss, pipeline, parameters]
                self.store_best_result(best_pipeline=pipeline, best_parameters=parameters)
        return best
