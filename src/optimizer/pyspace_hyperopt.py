#!/bin/env python
# -*- coding: utf-8 -*-
import os

import math
from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL
from pyspace_base_optimizer import PySPACEOptimizer
from . import optimizer
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pipelines.hyperopt_pipeline import HyperoptPipeline


@optimizer("HyperoptOptimizer")
class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, configuration, backend="serial"):
        super(HyperoptOptimizer, self).__init__(configuration, backend, pipeline_class=HyperoptPipeline)
        self._suggestion_algorithm = configuration.suggestion_algorithm if "suggestion_algorithm" in configuration \
            else tpe.suggest
        self._max_evaluations = configuration.max_evaluations if "max_evaluations" in configuration else 100
        self.__pipeline = None

    def optimize_pipeline(self, pipeline):
        self.__pipeline = pipeline
        pipeline_space = self.__pipeline.pipeline_space
        best_params = fmin(fn=self.__minimize,
                           space=pipeline_space,
                           algo=self._suggestion_algorithm,
                           max_evals=self._max_evaluations)
        return best_params

    def __minimize(self, spec):
        # Set all the parameters to be used
        for key, value in spec.iteritems():
            self.__pipeline.set_parameter(key, [value])

        try:
            result_path = self.__pipeline.execute(self._backend)
            summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
            return {
                "loss": -1 * summary[self._configuration.metric],
                "status": STATUS_OK
            }
        except Exception as e:
            return {
                "loss": float("inf"),
                "status": STATUS_FAIL
            }
