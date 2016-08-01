#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import shutil
import time
import warnings

import pySPACE
from hyperopt import STATUS_OK, tpe, STATUS_FAIL
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACE.tools.progressbar import ProgressBar, Percentage, Bar

from pySPACEOptimizer.core.optimizer_pool import OptimizerPool
from pySPACEOptimizer.framework.base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.framework.base_task import is_sink_node, is_source_node
from pySPACEOptimizer.hyperopt.hyperopt_node_parameter_space import HyperoptNodeParameterSpace, \
    ClassificationSinkNodeParameterSpace, ClassificationSourceNodeParameterSpace
from pySPACEOptimizer.hyperopt.persistent_trials import PersistentTrials
from pySPACEOptimizer.utils import output_logger, FileLikeLogger

BACKEND = None


# noinspection PyBroadException
def __minimize(spec):
    pipeline, parameter_setting = spec
    task = pipeline.configuration
    with output_logger(std_out_logger=None, std_err_logger=pipeline.error_logger):
        operation = pipeline.create_operation(parameter_settings=[parameter_setting])
    result_path = operation.get_output_directory()
    try:
        # Execute the pipeline
        # Log errors from here with special logger
        with output_logger(std_out_logger=None, std_err_logger=pipeline.error_logger):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipeline.execute(backend=BACKEND, operation=operation)
        # Check the result
        status = STATUS_OK
        result_file = os.path.join(result_path, "results.csv")
        if os.path.isfile(result_file):
            summary = PerformanceResultSummary.from_csv(result_file)
            # Calculate the mean of all data sets using the given metric
            if task["metric"] not in summary:
                raise ValueError("Metric '{metric}' not found in result data set".format(metric=task["metric"]))
            mean = numpy.mean(numpy.asarray(summary[task["metric"]], dtype=numpy.float))
            loss = -1 * mean if "is_performance_metric" in task and task["is_performance_metric"] else mean
        else:
            pipeline.logger.info("No results found. Returning inf")
            loss = float("inf")
            status = STATUS_FAIL
    except Exception:
        pipeline.error_logger.exception("Error minimizing the pipeline:")
        loss = float("inf")
        status = STATUS_FAIL
    finally:
        # Remove the result dir
        try:
            shutil.rmtree(result_path)
        except OSError as e:
            pipeline.logger.warn("Error while trying to delete the result dir: {error}".format(error=e.message))

    # noinspection PyUnboundLocalVariable
    return {
        "loss": loss,
        "status": status,
    }


def optimize_pipeline(task, pipeline, backend, queue):
    # Create the pipeline that should be optimized
    global BACKEND
    with output_logger(std_out_logger=None, std_err_logger=pipeline.error_logger):
        BACKEND = pySPACE.create_backend(backend)

    # Get the suggestion algorithm for the trials
    suggestion_algorithm = task["suggestion_algorithm"] if task["suggestion_algorithm"] else tpe.suggest

    # Get the number of evaluations to do in one pass
    evaluations = task["evaluations_per_pass"]
    passes = task["passes"]
    max_loss = task["max_loss"]
    check_after = task["check_after"]

    # noinspection PyBroadException
    try:
        # Create the trials object loading the persistent trials
        trials = PersistentTrials(trials_dir=pipeline.base_result_dir, fn=__minimize,
                                  space=(pipeline, pipeline.pipeline_space),
                                  recreate=task.get("restart_evaluation", False),
                                  rseed=int(time.time()))
        # Store the pipeline as an attachment to the trials
        trials.attachments["pipeline"] = pipeline

        # Log the pipeline
        pipeline.log_pipeline()

        # Do the evaluation
        best_trial = None
        for pass_ in range(1, passes + 1):
            pipeline.logger.info("-" * 10 + " Optimization pass: %d / %d " % (pass_, passes) + "-" * 10)
            # Create a progress bar
            progress_bar = ProgressBar(widgets=['Progress: ', Percentage(), ' ', Bar()],
                                       maxval=evaluations,
                                       fd=FileLikeLogger(logger=pipeline.logger, log_level=logging.INFO))
            pipeline.logger.debug("Minimizing the pipeline")
            for trial in trials.minimize(algo=suggestion_algorithm, evaluations=evaluations, pass_=pass_):
                pipeline.logger.debug("Trial: {trial.id} / Loss: {trial.loss}".format(trial=trial))
                # Put the result into the queue
                queue.put((trial.id, trial.loss, pipeline, trial.parameters(pipeline)))
                # Update the progress bar
                progress_bar.update(progress_bar.currval + 1)
                if best_trial is None or trial.loss <= best_trial.loss:
                    best_trial = trial
            if evaluations * pass_ >= check_after and best_trial.loss >= max_loss:
                pipeline.logger.warn("No pipeline found with loss better than %s after %s evaluations. Giving up" %
                                     (max_loss, check_after))
                parameters = best_trial.parameters(pipeline)
                for id_ in range(evaluations * pass_, evaluations * passes):
                    # Put inf loss to queue for every remaining evaluation
                    queue.put((id_, best_trial.loss, pipeline, parameters))
                # Then return to break the evaluation
                return
    except:
        pipeline.logger.exception("Error optimizing NodeChainParameterSpace:")


class HyperoptOptimizer(PySPACEOptimizer):
    """
    Optimizer to evaluate the processing pipelines and optimize the hyperparameters.

    This class implements an optimizer for the pySPACEOptimzier framework using the
    optimization library called `Hyperopt <https://github.com/hyperopt/hyperopt>`.
    Given an optimization task this class generates all valid processing pipelines,
    samples hyperparamter settings for them and evaluates these to find the best
    performing processing pipeline.
    """
    def __init__(self, task, backend, best_result_file):
        super(HyperoptOptimizer, self).__init__(task, backend, best_result_file)

    # noinspection PyBroadException
    def _do_optimization(self, pool):
        try:
            results = []
            self.logger.info("Starting processes")
            for node_chain in self._generate_node_chain_parameter_spaces():
                self.logger.debug("Enqueuing node chain '%s'" % node_chain)
                # Enqueue the evaluations and save the results
                results.append(pool.apply_async(func=optimize_pipeline,
                                                args=(self._task, node_chain, self._backend, self.queue)))
            self.logger.debug("Done starting processes")
            # close the pool
            pool.close()
            # Wait for the pipelines to finish
            self.logger.info("Waiting for the processes to finish")
            pool.join()
            # check the results
            self.logger.info("Checking the results of the processes")
            for result in results:
                self.logger.debug("Successful: %s" % result.successful())
                self.logger.debug("Result: %s" % result.get())
        except Exception:
            self.logger.exception("Error doing optimization. Giving up!")
            pool.terminate()
            pool.join()

    def optimize(self):
        self.logger.debug("Creating optimization pool")
        pool = OptimizerPool(processes=self._task["max_parallel_pipelines"])
        return self._do_optimization(pool)

    def _create_node(self, node_name):
        if is_sink_node(node_name):
            return ClassificationSinkNodeParameterSpace(node_name=node_name, task=self._task)
        elif is_source_node(node_name):
            return ClassificationSourceNodeParameterSpace(node_name=node_name, task=self._task)
        else:
            return HyperoptNodeParameterSpace(node_name=node_name, task=self._task)


class SerialHyperoptOptimizer(HyperoptOptimizer):
    def optimize(self):
        self.logger.debug("Creating optimization pool")
        # Create a pool with just one process, so every job
        # needs to be processed in serial
        pool = OptimizerPool(processes=1)
        return self._do_optimization(pool)
