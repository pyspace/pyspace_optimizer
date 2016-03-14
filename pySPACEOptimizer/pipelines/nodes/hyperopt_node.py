#!/bin/env python
# -*- coding: utf-8 -*-
from hyperopt import hp

from pySPACE.missions.nodes.decorators import UniformParameter, QUniformParameter, NormalParameter, QNormalParameter, \
    QLogNormalParameter, LogNormalParameter, QLogUniformParameter, LogUniformParameter
from pySPACEOptimizer.pipelines.nodes import PipelineNode, PipelineSinkNode, PipelineSourceNode


class HyperoptNode(PipelineNode):

    def __init__(self, node_name, task):
        super(HyperoptNode, self).__init__(node_name=node_name, task=task)

    def _handle_normal_parameter(self, name, parameter):
        if isinstance(parameter, QLogNormalParameter):
            return hp.qlognormal(name, parameter.mu, parameter.sigma, parameter.q)
        elif isinstance(parameter, LogNormalParameter):
            return hp.lognormal(name, parameter.mu, parameter.sigma)
        elif isinstance(parameter, QNormalParameter):
            return hp.qnormal(name, parameter.mu, parameter.sigma, parameter.q)
        elif isinstance(parameter, NormalParameter):
            return hp.normal(name, parameter.mu, parameter.sigma)

    def _handle_uniform_parameter(self, name, parameter):
        if isinstance(parameter, QLogUniformParameter):
            return hp.qloguniform(name, parameter.min, parameter.max, parameter.q)
        elif isinstance(parameter, LogUniformParameter):
            return hp.loguniform(name, parameter.min, parameter.max)
        elif isinstance(parameter, QUniformParameter):
            return hp.quniform(name, parameter.min, parameter.max, parameter.q)
        elif isinstance(parameter, UniformParameter):
            return hp.uniform(name, parameter.min, parameter.max)

    def _handle_choice_parameter(self, name, parameter):
        return hp.choice(name, parameter.choices)


class HyperoptSinkNode(PipelineSinkNode):
    pass


class HyperoptSourceNode(PipelineSourceNode):
    pass
