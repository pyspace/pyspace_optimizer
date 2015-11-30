#!/bin/env python
# -*- coding: utf-8 -*-
import abc


__all__ = ["PySPACEOptimizer", "NoPipelineFound"]


class NoPipelineFound(Exception):
    def __init__(self, input_type, length):
        super(Exception, self).__init__()
        self.__length = length
        self.__input_type = input_type

    def __repr__(self):
        return "No pipeline with length %d could be found for input type '%s'" % (self.__length, self.__input_type)

    def __str__(self):
        return repr(self)


class PySPACEOptimizer(object):

    __metaclass__ = abc.ABCMeta

    # TODO: Insert a good default metric!
    def __init__(self, configuration, backend="serial"):
        self._configuration = configuration
        self._backend = backend

    @abc.abstractmethod
    def optimize(self):
        raise NotImplementedError()
