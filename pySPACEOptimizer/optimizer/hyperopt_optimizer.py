#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import time
import warnings

import sys
from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL
from hyperopt.mongoexp import MongoTrials, main_worker

from base_optimizer import PySPACEOptimizer
from optimizer_pool import OptimizerPool
from multiprocessing import Process
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node

LOGGER = logging.getLogger("pySPACEOptimizer.optimizer.HyperoptOptimizer")
LOGGER.setLevel(logging.DEBUG)


def __minimize(spec):
    task, pipeline, backend = spec[0]
    parameter_ranges = {param: [value] for param, value in spec[1].iteritems()}
    try:
        with warnings.catch_warnings():
            # Ignore all warnings shown by the pipeline as most of them occur because of the parameters selected
            warnings.simplefilter("ignore")
            result_path = pipeline.execute(parameter_ranges=parameter_ranges, backend=backend)
        summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
        # Calculate the mean of all data sets using the given metric
        mean = numpy.mean(numpy.asarray(summary[task["metric"]], dtype=numpy.float))
        return {
            "loss": -1 * mean if "is_performance_metric" in task and
                                 task["is_performance_metric"] else mean,
            "status": STATUS_OK
        }
    except Exception:
        return {
            "loss": float("inf"),
            "status": STATUS_FAIL
        }


def __worker(mongodb_connection):
    old_argv = sys.argv
    try:
        # Replace the system arguments
        sys.argv = [__file__, "--mongo=%s" % mongodb_connection, "--poll-interval=5"]
        # Start the worker
        main_worker()
    finally:
        sys.argv = old_argv


def optimize_pipeline(args):
    task, pipeline, _ = args
    pipeline_space = [args, pipeline.pipeline_space]
    connection = task["mongodb_connection"] if "mongodb_connection" in task else "mongo://localhost:1234/"
    # Store each pipeline in it's own db
    connection += "%s" % hash(pipeline)
    # TODO: Enable usage of different backends (maybe clustering?!)
    process = Process(target=__worker, args=(connection,))
    try:
        process.start()
        trials = MongoTrials(connection + "/jobs")
        best = fmin(fn=__minimize,
                    space=pipeline_space,
                    algo=task["suggestion_algorithm"] if "suggestion_algorithm" in task else tpe.suggest,
                    max_evals=task["max_evaluations"] if "max_evaluations" in task else 100,
                    trials=trials)
        return trials.best_trial["result"]["loss"], pipeline, best
    finally:
        process.terminate()
        process.join()


class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, task, backend="serial"):
        super(HyperoptOptimizer, self).__init__(task, backend)

    def optimize(self):
        def _optimize():
            for pipeline in PipelineGenerator(self._task):
                pipeline = Pipeline(configuration=self._task,
                                    node_chain=[self._create_node(node_name) for node_name in pipeline])
                yield (self._task, pipeline, self._backend)
                # We need to wait at least one second before yielding the next pipeline
                # otherwise the result will be stored within the same result dir
                time.sleep(1)

        # TODO: Enable usage of different backends (maybe clustering?!)
        pool = OptimizerPool()
        results = pool.imap(optimize_pipeline, _optimize())
        pool.close()

        # loss, pipeline, parameters
        best = [float("inf"), None, None]
        for loss, pipeline, parameters in results:
            if loss < best[0]:
                best = [loss, pipeline, parameters]

        pool.join()
        # Return the best result
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
        def _optimize():
            for pipeline in PipelineGenerator(self._task):
                pipeline = Pipeline(configuration=self._task,
                                    node_chain=[self._create_node(node_name) for node_name in pipeline])
                yield (self._task, pipeline, self._backend)

        results = []
        for args in _optimize():
            results.append(optimize_pipeline(args))

        best = [None, float("inf")]
        for params, loss in results:
            LOGGER.warning("Checking Result: Params: %s \nLoss: %s" % (params, loss))
            if loss < best[1]:
                best = [params, loss]

        return best[0]
