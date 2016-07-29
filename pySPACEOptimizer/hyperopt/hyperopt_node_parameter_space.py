#!/bin/env python
# -*- coding: utf-8 -*-
import math
from hyperopt import hp

from pySPACE.missions.nodes.decorators import UniformParameter, QUniformParameter, NormalParameter, QNormalParameter, \
    QLogNormalParameter, LogNormalParameter, QLogUniformParameter, LogUniformParameter, ChoiceParameter
from pySPACEOptimizer.framework.node_parameter_space import NodeParameterSpace, SinkNodeParameterSpace, \
    SourceNodeParameterSpace


class HyperoptNodeParameterSpace(NodeParameterSpace):

    def __init__(self, node_name, task):
        super(HyperoptNodeParameterSpace, self).__init__(node_name=node_name, task=task)

    def _handle_parameter(self, name, parameter):
        if isinstance(parameter, LogNormalParameter):
            value = self._handle_lognormal_parameter(name, parameter)
        elif isinstance(parameter, NormalParameter):
            value = self._handle_normal_parameter(name, parameter)
        elif isinstance(parameter, UniformParameter):
            value = self._handle_uniform_parameter(name, parameter)
        elif isinstance(parameter, ChoiceParameter):
            value = self._handle_choice_parameter(name, parameter)
        else:
            value = parameter
        return value

    @staticmethod
    def _handle_lognormal_parameter(name, parameter):
        if isinstance(parameter, QLogNormalParameter):
            return hp.qlognormal(name, math.log(parameter.scale), parameter.shape, parameter.q)
        elif isinstance(parameter, LogNormalParameter):
            return hp.lognormal(name, math.log(parameter.scale), parameter.shape)

    @staticmethod
    def _handle_normal_parameter(name, parameter):
        if isinstance(parameter, QNormalParameter):
            return hp.qnormal(name, parameter.mu, parameter.sigma, parameter.q)
        elif isinstance(parameter, NormalParameter):
            return hp.normal(name, parameter.mu, parameter.sigma)

    @staticmethod
    def _handle_uniform_parameter(name, parameter):
        if isinstance(parameter, QLogUniformParameter):
            return hp.qloguniform(name, math.log(parameter.min - parameter.q / 2.0),
                                  math.log(parameter.max + parameter.q / 2.0), parameter.q)
        elif isinstance(parameter, LogUniformParameter):
            return hp.loguniform(name, math.log(parameter.min), math.log(parameter.max))
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


class ClassificationSinkNodeParameterSpace(SinkNodeParameterSpace):
    def __init__(self, node_name, task):
        super(SinkNodeParameterSpace, self).__init__(node_name, task=task)
        self._main_class = task["main_class"]
        self._class_labels = task["class_labels"]
        self._property = "ir_class"

    def as_dictionary(self):
        result = super(SinkNodeParameterSpace, self).as_dictionary()
        if "parameters" not in result:
            result["parameters"] = {}
        result["parameters"]["ir_class"] = self._main_class
        result["parameters"]["classes_names"] = self._class_labels
        return result


class ClassificationSourceNodeParameterSpace(SourceNodeParameterSpace):
    pass
