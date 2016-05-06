#!/bin/env python
# -*- coding: utf-8 -*-
from hyperopt import hp

from pySPACE.missions.nodes.decorators import UniformParameter, QUniformParameter, NormalParameter, QNormalParameter, \
    QLogNormalParameter, LogNormalParameter, QLogUniformParameter, LogUniformParameter, ChoiceParameter
from pySPACEOptimizer.framework.node_parameter_space import NodeParameterSpace, SinkNodeParameterSpace, \
    SourceNodeParameterSpace


class HyperoptNodeParameterSpace(NodeParameterSpace):

    def __init__(self, node_name, task):
        super(HyperoptNodeParameterSpace, self).__init__(node_name=node_name, task=task)

    def _handle_parameter(self, name, parameter):
        if isinstance(parameter, NormalParameter):
            value = self._handle_normal_parameter(name, parameter)
        elif isinstance(parameter, UniformParameter):
            value = self._handle_uniform_parameter(name, parameter)
        elif isinstance(parameter, ChoiceParameter):
            value = self._handle_choice_parameter(name, parameter)
        else:
            value = parameter
        return value

    @staticmethod
    def _handle_normal_parameter(name, parameter):
        if isinstance(parameter, QLogNormalParameter):
            return hp.qlognormal(name, parameter.mu, parameter.sigma, parameter.q)
        elif isinstance(parameter, LogNormalParameter):
            return hp.lognormal(name, parameter.mu, parameter.sigma)
        elif isinstance(parameter, QNormalParameter):
            return hp.qnormal(name, parameter.mu, parameter.sigma, parameter.q)
        elif isinstance(parameter, NormalParameter):
            return hp.normal(name, parameter.mu, parameter.sigma)

    @staticmethod
    def _handle_uniform_parameter(name, parameter):
        if isinstance(parameter, QLogUniformParameter):
            return hp.qloguniform(name, parameter.min, parameter.max, parameter.q)
        elif isinstance(parameter, LogUniformParameter):
            return hp.loguniform(name, parameter.min, parameter.max)
        elif isinstance(parameter, QUniformParameter):
            return hp.quniform(name, parameter.min, parameter.max, parameter.q)
        elif isinstance(parameter, UniformParameter):
            return hp.uniform(name, parameter.min, parameter.max)

    @staticmethod
    def _handle_choice_parameter(name, parameter):
        return hp.choice(name, parameter.choices)

    def parameter_space(self):
        return {name: self._handle_parameter(name, parameter)
                for name, parameter in super(HyperoptNodeParameterSpace, self).parameter_space().items()}


class HyperoptSinkNodeParameterSpace(SinkNodeParameterSpace):
    pass


class HyperoptSourceNodeParameterSpace(SourceNodeParameterSpace):
    pass
