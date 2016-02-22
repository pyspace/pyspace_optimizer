#!/bin/env python
# -*- coding: utf-8 -*-
import abc
import os

from pySPACEOptimizer.pipelines import Pipeline


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

    def __init__(self, task, backend, best_result_file):
        """
        :type task: Task
        :type backend: str
        :type best_result_file: File
        """
        self._task = task
        self._backend = backend
        self._best_result_file = best_result_file if best_result_file is not None else "%s_best.yaml" % task["data_set_path"]

    def store_best_result(self, best_pipeline, best_parameters):
        """
        :type best_pipeline: Pipeline
        :type best_parameters: dict[str, list[object]]
        """
        parameter_ranges = {param: [value] for param, value in best_parameters.iteritems()}
        operation_spec = best_pipeline.operation_spec(parameter_ranges=parameter_ranges)
        with open(self._best_result_file, "wb") as best_result_file:
            # Write the result to the object
           best_result_file.write(operation_spec["base_file"])

    @abc.abstractmethod
    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.

        :return: The best parameters found for this pipeline
        :rtype: dict[str, object]
        """
        raise NotImplementedError()
