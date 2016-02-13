#!/bin/env python
# -*- coding: utf-8 -*-
import abc
try:
    from cPickle import dump
except ImportError:
    from pickle import dump


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

    def __init__(self, task, backend="serial", best_result_file="best_result.pickle"):
        self._task = task
        self._backend = backend
        self._best_result = best_result_file

    def store_best_result(self, best_result):
        dump(best_result, self._best_result)

    @abc.abstractmethod
    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.

        :return: The best parameters found for this pipeline
        :rtype: dict[str, object]
        """
        raise NotImplementedError()
