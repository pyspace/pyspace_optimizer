#!/bin/env python
# -*- coding: utf-8 -*-
from hyperopt import hp

from pySPACE.missions.nodes.decorators import UniformParameter, QUniformParameter, NormalParameter, QNormalParameter, \
    ChoiceParameter
from pySPACEOptimizer.pipelines.nodes import PipelineNode, PipelineSinkNode, PipelineSourceNode


class HyperoptNode(PipelineNode):

    def __init__(self, node_name, task):
        super(HyperoptNode, self).__init__(node_name=node_name, task=task)

    def parameter_space(self):
        space = {}
        for key, value in super(HyperoptNode, self).parameter_space().iteritems():
            if isinstance(value, QUniformParameter):
                space[key] = hp.qloguniform(key, value.min, value.max, value.q)
            elif isinstance(value, UniformParameter):
                space[key] = hp.loguniform(key, value.min, value.max)
            elif isinstance(value, QNormalParameter):
                space[key] = hp.qlognormal(key, value.mu, value.sigma, value.q)
            elif isinstance(value, NormalParameter):
                space[key] = hp.lognormal(key, value.mu, value.sigma)
            elif isinstance(value, ChoiceParameter):
                space[key] = hp.choice(key, value.choices)
        return space


class HyperoptSinkNode(PipelineSinkNode):
    pass


class HyperoptSourceNode(PipelineSourceNode):
    pass
