#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy
import os
import time
import warnings

from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL, Trials

from base_optimizer import PySPACEOptimizer
from optimizer_pool import OptimizerPool
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node

LOGGER = logging.getLogger("pySPACEOptimizer.optimizer.HyperoptOptimizer")
LOGGER.setLevel(logging.DEBUG)


def optimize_pipeline(args):
    configuration, pipeline, backend = args

    def __minimize(spec):
        parameter_ranges = {param: [value] for param, value in spec.iteritems()}
        try:
            with warnings.catch_warnings():
                # Ignore all warnings shown by the pipeline as most of them occur because of the parameters selected
                warnings.simplefilter("ignore")
                result_path = pipeline.execute(parameter_ranges=parameter_ranges, backend=backend)
            summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
            # Calculate the mean of all data sets using the given metric
            mean = numpy.mean(numpy.asarray(summary[configuration["metric"]], dtype=numpy.float))
            return {
                "loss": -1 * mean if "is_performance_metric" in configuration and
                                     configuration["is_performance_metric"] else mean,
                "status": STATUS_OK
            }
        except Exception:
            return {
                "loss": float("inf"),
                "status": STATUS_FAIL
            }

    pipeline_space = pipeline.pipeline_space
    # TODO: Make the Trials-Object reloadable from aborted tests
    trials = Trials()
    best = fmin(fn=__minimize,
                space=pipeline_space,
                algo=configuration["suggestion_algorithm"] if "suggestion_algorithm" in configuration else tpe.suggest,
                max_evals=configuration["max_evaluations"] if "max_evaluations" in configuration else 100,
                trials=trials)
    return trials.best_trial["result"]["loss"], pipeline, best


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
