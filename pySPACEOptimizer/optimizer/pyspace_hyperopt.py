#!/bin/env python
# -*- coding: utf-8 -*-
import os
from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL, Trials
from pySPACEOptimizer.configuration import is_sink_node, is_source_node
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pyspace_base_optimizer import PySPACEOptimizer
from . import optimizer
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from multiprocessing.pool import Pool


def optimize_pipeline(args):
    configuration, pipeline, backend = args

    def __minimize(spec):
        parameter_ranges = {param: [value] for param, value in spec.iteritems()}
        try:
            result_path = pipeline.execute(parameter_ranges=parameter_ranges, backend=backend)
            summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
            return {
                "loss": -1 * summary[configuration.metric],
                "status": STATUS_OK
            }
        except Exception as e:
            return {
                "loss": float("inf"),
                "status": STATUS_FAIL
            }

    pipeline_space = pipeline.pipeline_space
    # TODO: Make the Trials-Object reloadable from aborted tests
    trials = Trials()
    best = fmin(fn=__minimize,
                space=pipeline_space,
                algo=configuration.suggestion_algorithm if "suggestion_algorithm" in configuration else tpe.suggest,
                max_evals=configuration.max_evaluations if "max_evaluations" in configuration else 100,
                trials=trials)
    return best, trials.best_trial["result"]["loss"]


@optimizer("HyperoptOptimizer")
class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, configuration, backend="serial"):
        super(HyperoptOptimizer, self).__init__(configuration, backend)

    def optimize(self):
        def _optimize():
            for pipeline in PipelineGenerator(self._configuration):
                pipeline = Pipeline(configuration=self._configuration,
                                    node_chain=[self._create_node(node_name) for node_name in pipeline])
                yield (self._configuration, pipeline, self._backend)

#        pool = Pool()
#        results = pool.imap_unordered(optimize_pipeline, _optimize())
#        pool.close()
        results = []
        for args in _optimize():
            results.append(optimize_pipeline(args))

        best = [None, float("inf")]
        for params, loss in results:
            if loss < best[1]:
                best = [params, loss]
        #pool.join()
        return best[0]

    def _create_node(self, node_name):
        if is_sink_node(node_name):
            return HyperoptSinkNode(node_name=node_name, configuration=self._configuration)
        elif is_source_node(node_name):
            return HyperoptSourceNode(node_name=node_name, configuration=self._configuration)
        else:
            return HyperoptNode(node_name=node_name, configuration=self._configuration)
