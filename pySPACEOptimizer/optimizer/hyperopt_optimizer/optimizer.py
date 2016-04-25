#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import time
import warnings
from Queue import Empty
from multiprocessing import Manager

from hyperopt import STATUS_OK, tpe, STATUS_FAIL
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACE.tools.progressbar import ProgressBar, Percentage, Bar

from pySPACEOptimizer.optimizer.base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.optimizer.hyperopt_optimizer.persistent_trials import MultiprocessingPersistentTrials, \
    PersistentTrials
from pySPACEOptimizer.optimizer.optimizer_pool import OptimizerPool
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node
from pySPACEOptimizer.utils import OutputLogger, FileLikeLogger


def __minimize(spec):
    pipeline, backend = spec[0]
    task = pipeline.configuration
    logger = pipeline.get_logger()
    parameter_ranges = {param: [value] for param, value in spec[1].items()}
    # noinspection PyBroadException
    try:
        # Execute the pipeline
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result_path = pipeline.execute(parameter_ranges=parameter_ranges,
                                           backend=backend)
        # Check the result
        result_file = os.path.join(result_path, "results.csv") if result_path is not None else ""
        if os.path.isfile(result_file):
            summary = PerformanceResultSummary.from_csv(result_file)
            # Calculate the mean of all data sets using the given metric
            if task["metric"] not in summary:
                raise ValueError("Metric '{metric}' not found in result data set".format(metric=task["metric"]))

            mean = numpy.mean(numpy.asarray(summary[task["metric"]], dtype=numpy.float))

            loss = -1 * mean if "is_performance_metric" in task and task["is_performance_metric"] else mean
            status = STATUS_OK
        else:
            logger.debug("No results found. "
                         "Returning infinite loss and failed state")
            loss = float("inf"),
            status = STATUS_FAIL
    except Exception:
        logger.exception("Error minimizing the pipeline:")
        loss = float("inf"),
        status = STATUS_FAIL

    logger.debug("Loss: {loss:.3f}".format(loss=loss))
    return {
        "loss": loss,
        "status": status
    }


def optimize_pipeline(backend, queue, pipeline, evaluations, pass_, trials_class=PersistentTrials):
    # Get the base result dir and append it to the arguments
    # Store each pipeline in it's own folder
    task = pipeline.configuration
    if not os.path.isdir(pipeline.base_result_dir):
        os.makedirs(pipeline.base_result_dir)
    suggestion_algorithm = task["suggestion_algorithm"] if task["suggestion_algorithm"] else tpe.suggest
    pipeline_space = [(pipeline, backend), pipeline.pipeline_space]
    # Create the trials object loading the persistent trials
    try:
        trials = trials_class(trials_dir=pipeline.base_result_dir)
        # Do the evaluation
        # Log errors from here with special logger
        with OutputLogger(std_out_logger=None,
                          std_err_logger=pipeline.get_error_logger()):
            for trial in trials.minimize(fn=__minimize,
                                         space=pipeline_space,
                                         algo=suggestion_algorithm,
                                         evaluations=evaluations,
                                         pass_=pass_,
                                         rseed=int(time.time())):
                # Put the result into the queue
                queue.put((trial.id, trial.loss, pipeline, trial.parameters(pipeline)))
    except IOError:
        pipeline.get_error_logger().exception("Error optimizing Pipeline:")


class HyperoptOptimizer(PySPACEOptimizer):
    TRIALS_CLASS = MultiprocessingPersistentTrials

    def __init__(self, task, backend, best_result_file):
        super(HyperoptOptimizer, self).__init__(task, backend, best_result_file)
        manager = Manager()
        self._queue = manager.Queue()

    def _do_optimization(self, evaluations, pass_, performance_graphic):
        self._logger.debug("Creating optimization pool")
        pool = OptimizerPool()

        try:
            pipelines = []
            results = []
            self._logger.debug("Generating pipelines")
            for pipeline in self._generate_pipelines():
                # Enqueue the evaluations and save the results
                results.append(pool.apply_async(func=optimize_pipeline,
                                                args=(self._backend, self._queue, pipeline, evaluations, pass_,
                                                      self.TRIALS_CLASS)))
                pipelines.append(pipeline)
            self._logger.debug("Done generating pipelines")

            # close the pool
            pool.close()
            # Read the queue until all jobs are done or the max evaluation time is reached
            return self._read_queue(pipelines=pipelines, max_evals=evaluations, results=results,
                                    performance_graphic=performance_graphic)
        except Exception:
            self._logger.exception("Error doing optimization pass, returning infinite loss.")
            return float("inf"), None, None
        finally:
            pool.terminate()
            pool.join()

    def _read_queue(self, pipelines, max_evals, results, performance_graphic):
        self._logger.debug("Reading queue")
        best = [float("inf"), None, None]
        # Create a progress bar
        progress_bar = ProgressBar(widgets=['Progress: ', Percentage(), ' ', Bar()],
                                   maxval=max_evals * len(results),
                                   fd=FileLikeLogger(logger=self._logger, log_level=logging.INFO))
        while True:
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
                    id, loss, pipeline, parameters = result
                    self._logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s",
                                       pipeline, loss, parameters)
                    if loss < best[0]:
                        best = [loss, pipeline, parameters]
                        self.store_best_result(best_pipeline=pipeline,
                                               best_parameters=parameters)
                    performance_graphic.add(pipeline, id, loss)
                    # Update the performance graphic
                    progress_bar.update(progress_bar.currval + 1)
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


class HyperoptOptimizerSerialTrials(HyperoptOptimizer):
    TRIALS_CLASS = PersistentTrials


class SerialHyperoptOptimizer(HyperoptOptimizer):
    def _do_optimization(self, evaluations, pass_, performance_graphic):
        self._logger.debug("Creating optimization pool")
        # Create a pool with just one process, so every job
        # needs to be processed in serial
        pool = OptimizerPool(processes=1)
        try:
            pipelines = []
            results = []
            self._logger.debug("Generating pipelines")
            for pipeline in self._generate_pipelines():
                # Enqueue the evaluations and save the results
                results.append(pool.apply_async(func=optimize_pipeline,
                                                args=(self._backend, self._queue, pipeline, evaluations, pass_,
                                                      self.TRIALS_CLASS)))
                pipelines.append(pipeline)
            self._logger.debug("Done generating pipelines")

            # close the pool
            pool.close()
            # Read the queue until all jobs are done or the max evaluation time is reached
            return self._read_queue(pipelines=pipelines, max_evals=evaluations, results=results,
                                    performance_graphic=performance_graphic)
        finally:
            pool.terminate()
            pool.join()


class SerialHyperoptOptimizerSerialTrials(SerialHyperoptOptimizer):
    TRIALS_CLASS = PersistentTrials
