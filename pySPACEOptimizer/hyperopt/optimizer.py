#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import time
import warnings
from Queue import Empty
from multiprocessing import Manager

import shutil
from hyperopt import STATUS_OK, tpe, STATUS_FAIL

import pySPACE
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACE.tools.progressbar import ProgressBar, Percentage, Bar, ETA
from pySPACEOptimizer.core.optimizer_pool import OptimizerPool
from pySPACEOptimizer.framework.base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.framework.base_task import is_sink_node, is_source_node
from pySPACEOptimizer.hyperopt.hyperopt_node_parameter_space import HyperoptNodeParameterSpace, \
    HyperoptSinkNodeParameterSpace, HyperoptSourceNodeParameterSpace
from pySPACEOptimizer.hyperopt.persistent_trials import PersistentTrials
from pySPACEOptimizer.utils import output_logger, FileLikeLogger


def __minimize(spec):
    pipeline, backend = spec[0]
    task = pipeline.configuration
    parameter_settings = [spec[1]]
    # noinspection PyBroadException
    try:
        # Execute the pipeline
        # Log errors from here with special logger
        with output_logger(std_out_logger=None, std_err_logger=pipeline.error_logger):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result_path = pipeline.execute(backend=backend, parameter_settings=parameter_settings)
        # Check the result
        summary = PerformanceResultSummary(dataset_dir=result_path)
        # Calculate the mean of all data sets using the given metric
        if task["metric"] not in summary.data:
            raise ValueError("Metric '{metric}' not found in result data set".format(metric=task["metric"]))
        mean = numpy.mean(numpy.asarray(summary.data[task["metric"]], dtype=numpy.float))
        loss = -1 * mean if "is_performance_metric" in task and task["is_performance_metric"] else mean
        status = STATUS_OK
        # Remove the result dir
        try:
            shutil.rmtree(result_path)
        except OSError as e:
            pipeline.logger.warn("Error while trying to delete the result dir: {error}".format(error=e.message))
    except Exception:
        pipeline.logger.exception("Error minimizing the pipeline:")
        loss = float("inf")
        status = STATUS_FAIL

    pipeline.logger.debug("Loss: {loss:.3f}".format(loss=loss))
    return {
        "loss": loss,
        "status": status,
    }


def optimize_pipeline(task, pipeline, backend, queue):
    # Create the pipeline that should be optimized
    with output_logger(std_out_logger=None, std_err_logger=pipeline.error_logger):
        backend = pySPACE.create_backend(backend)

    # Get the suggestion algorithm for the trials
    suggestion_algorithm = task["suggestion_algorithm"] if task["suggestion_algorithm"] else tpe.suggest

    # Get the number of evaluations to do in one pass
    evaluations = task["evaluations_per_pass"]
    passes = task["passes"]

    try:
        # Create the trials object loading the persistent trials
        trials = PersistentTrials(trials_dir=pipeline.base_result_dir, recreate=task.get("restart_evaluation", False))

        # Do the evaluation
        for pass_ in range(1, passes + 1):
            pipeline.logger.info("-" * 10 + " Optimization pass: %d / %d " % (pass_, passes) + "-" * 10)
            # Create a progress bar
            progress_bar = ProgressBar(widgets=['Progress: ', Percentage(), ' ', Bar()],
                                       maxval=evaluations,
                                       fd=FileLikeLogger(logger=pipeline.logger, log_level=logging.INFO))
            for trial in trials.minimize(fn=__minimize, space=((pipeline, backend), pipeline.pipeline_space),
                                         algo=suggestion_algorithm, evaluations=evaluations, pass_=pass_,
                                         rseed=int(time.time())):
                # Put the result into the queue
                queue.put((trial.id, trial.loss, pipeline, trial.parameters(pipeline)))
                # Update the progress bar
                progress_bar.update(progress_bar.currval + 1)
    except IOError:
        pipeline.error_logger.exception("Error optimizing NodeChainParameterSpace:")


class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, task, backend, best_result_file):
        super(HyperoptOptimizer, self).__init__(task, backend, best_result_file)
        manager = Manager()
        self._queue = manager.Queue()

    # noinspection PyBroadException
    def _do_optimization(self, pool):
        try:
            results = []
            self.logger.debug("Generating pipelines")
            for node_chain in self._generate_node_chain_parameter_spaces():
                # Enqueue the evaluations and save the results
                results.append(pool.apply_async(func=optimize_pipeline,
                                                args=(self._task, node_chain, self._backend, self._queue)))
            self.logger.debug("Done generating pipelines")

            # close the pool
            pool.close()
            # Read the queue until all jobs are done or the max evaluation time is reached
            return self._read_queue(results=results)
        except Exception:
            self.logger.exception("Error doing optimization pass, returning infinite loss.")
            return float("inf"), None, None
        finally:
            pool.terminate()
            pool.join()

    def optimize(self):
        self.logger.debug("Creating optimization pool")
        pool = OptimizerPool()
        return self._do_optimization(pool)

    def _read_queue(self, results):
        self.logger.debug("Reading queue")
        best = [float("inf"), None, None]
        evaluations = self._task["evaluations_per_pass"]
        passes = self._task["passes"]
        # Create a progress bar
        progress_bar = ProgressBar(widgets=['Progress: ', Percentage(), ' ', Bar(), ' ', ETA()],
                                   maxval=evaluations * passes * len(results),
                                   fd=FileLikeLogger(logger=self._logger, log_level=logging.INFO))
        progress_bar.update(0)
        while True:
            if self._queue.empty() and results is not None and all([result.ready() for result in results]):
                # the queue is empty and all workers are finished: break
                # but first check for errors:
                for result in results:
                    if not result.successful():
                        self.logger.error(result.get())
                break
            else:
                try:
                    result = self._queue.get(timeout=1)
                    id_, loss, pipeline, parameters = result
                    self.logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s",
                                      pipeline, loss, parameters)
                    if loss < best[0]:
                        best = [loss, pipeline, parameters]
                        self._store_best_result(best_pipeline=pipeline,
                                                best_parameters=parameters)
                    # Update the progress bar
                    progress_bar.update(progress_bar.currval + 1)
                    # Update the performance graphic
                    self._performance_graphic_add(pipeline, id_, loss)
                except Empty:
                    pass
        else:
            self.logger.info("Reached maximal evaluation time, breaking evaluation")
        return best

    def _create_node(self, node_name):
        if is_sink_node(node_name):
            return HyperoptSinkNodeParameterSpace(node_name=node_name, task=self._task)
        elif is_source_node(node_name):
            return HyperoptSourceNodeParameterSpace(node_name=node_name, task=self._task)
        else:
            return HyperoptNodeParameterSpace(node_name=node_name, task=self._task)


class SerialHyperoptOptimizer(HyperoptOptimizer):
    def optimize(self):
        self.logger.debug("Creating optimization pool")
        # Create a pool with just one process, so every job
        # needs to be processed in serial
        pool = OptimizerPool(processes=1)
        return self._do_optimization(pool)
