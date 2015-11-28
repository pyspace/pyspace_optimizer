#!/bin/env python
# -*- coding: utf-8 -*-
import os
import uuid
import pySPACE
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from hyperopt import hp, fmin, STATUS_OK, tpe
from pipeline_generator import PipelineGenerator
from pipeline import PipelineNode, Pipeline
from pyspace_base_optimizer import PySPACEOptimizer


class HyperoptPipelineNode(PipelineNode):

    def __init__(self, node_name, uuid_=None):
        if uuid_ is None:
            uuid_ = uuid.uuid4()
        self.__uuid = uuid_
        super(HyperoptPipelineNode, self).__init__(node_name)

    def make_parameter_name(self, parameter):
        return "__{uuid}_{node_name}_{parameter}__".format(
            uuid=self.__uuid.get_hex(),
            node_name=self.name,
            parameter=parameter
        )

    @property
    def parameter_space(self):
        space = {}
        for key, value in super(HyperoptPipelineNode, self).parameter_space.iteritems():
            if isinstance(value, (int, float)):
                # Default: Create a normal distribution around the default value with sigma=1
                space[key] = hp.lognormal(key, value, 1)
            else:
                # Create a choice with only one value
                space[key] = hp.choice(key, [value])
        return space


class HyperoptPipeline(Pipeline):

    @classmethod
    def from_node_list(cls, node_list, data_set_path):
        nodes = [HyperoptPipelineNode(node) for node in node_list]
        return HyperoptPipeline(nodes, data_set_path)


class PySPACEHyperopt(PySPACEOptimizer):

    def __init__(self, data_set_dir, max_pipeline_length, metric, backend="serial",
                 suggestion_algorithm=tpe.suggest, max_evaluations=100):
        super(PySPACEHyperopt, self).__init__(data_set_dir, metric)
        self.__max_pipeline_length = max_pipeline_length
        self.__backend = pySPACE.create_backend(backend)
        self.__suggestion_algorithm = suggestion_algorithm
        self.__max_evaluations = max_evaluations
        self.__pipelines = []

    def optimize(self):
        self.__pipelines = []
        pipeline_spaces = []
        i = 0
        for pipeline in PipelineGenerator(self.data_set_type, self.__max_pipeline_length):
            pipeline = HyperoptPipeline.from_node_list(pipeline, self.data_set_dir)
            self.__pipelines.append(pipeline)
            pipeline_space = pipeline.pipeline_space
            pipeline_spaces.append((i, pipeline_space))
            i += 1
        space = hp.choice("pipeline", pipeline_spaces)
        best_params = fmin(fn=self.__minimize,
                           space=space,
                           algo=self.__suggestion_algorithm,
                           max_evals=self.__max_evaluations)
        return best_params

    def __minimize(self, spec):
        # First get the pipeline to execute
        pipeline_number = spec[0]
        pipeline = self.__pipelines[pipeline_number]
        # Set all the parameters to be used
        for key, value in spec[1].iteritems():
            pipeline.set_parameter(key, value)
        operation = pySPACE.create_operation(pipeline)
        result_path = pySPACE.run_operation(self.__backend, operation)
        summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
        return {
            "loss": -1 * summary[self.metric],
            "status": STATUS_OK
        }
