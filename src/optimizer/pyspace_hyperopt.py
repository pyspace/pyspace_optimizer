#!/bin/env python
# -*- coding: utf-8 -*-
import os
from hyperopt import hp, fmin, STATUS_OK, tpe, STATUS_FAIL
from pyspace_base_optimizer import PySPACEOptimizer, NoPipelineFound
from . import optimizer
from pipeline_generator import PipelineGenerator
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pipelines.hyperopt_pipeline import HyperoptPipeline


@optimizer("HyperoptOptimizer")
class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, configuration, backend="serial"):
        super(HyperoptOptimizer, self).__init__(configuration, backend)
        self._suggestion_algorithm = configuration.suggestion_algorithm if "suggestion_algorithm" in configuration \
            else tpe.suggest
        self._max_evaluations = configuration.max_evaluations if "max_evaluations" in configuration else 100
        self._pipelines = []

    def optimize(self):
        self._pipelines = []
        pipeline_spaces = []
        i = 0
        for pipeline in PipelineGenerator(self._configuration):
            pipeline = HyperoptPipeline.from_node_list(pipeline, self._configuration.data_set_path)
            self._pipelines.append(pipeline)
            pipeline_space = pipeline.pipeline_space
            pipeline_spaces.append((i, pipeline_space))
            i += 1
        if not pipeline_spaces:
            # No pipeline could be constructed, raise NoPipelineFound-exception
            raise NoPipelineFound(self._configuration.data_set_type, self._configuration.max_processing_length)

        # Construct the hyperopt space and minimize it
        space = hp.choice("pipeline", pipeline_spaces)
        best_params = fmin(fn=self.__minimize,
                           space=space,
                           algo=self._suggestion_algorithm,
                           max_evals=self._max_evaluations)
        return best_params

    def __minimize(self, spec):
        # First get the pipeline to execute
        pipeline_number = spec[0]
        pipeline = self._pipelines[pipeline_number]
        # Set all the parameters to be used
        for key, value in spec[1].iteritems():
            pipeline.set_parameter(key, [value])
        try:
            result_path = pipeline.execute(self._backend)
            summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
            return {
                "loss": -1 * summary[self._configuration.metric],
                "status": STATUS_OK
            }
        except Exception:
            return {
                "status": STATUS_FAIL
            }
