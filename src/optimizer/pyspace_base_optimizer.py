#!/bin/env python
# -*- coding: utf-8 -*-
import abc
from pipelines import Pipeline


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

    def __init__(self, configuration, backend="serial", pipeline_class=Pipeline):
        self._configuration = configuration
        self._backend = backend
        self._pipeline_class = pipeline_class

    def optimize(self):
        from pipeline_generator import PipelineGenerator
        no_pipeline_found = True
        for pipeline in PipelineGenerator(self._configuration, pipeline_class=self._pipeline_class):
            no_pipeline_found = False
            self.optimize_pipeline(pipeline)

        if no_pipeline_found:
            # No pipeline could be constructed, raise NoPipelineFound-exception
            raise NoPipelineFound(self._configuration.data_set_type, self._configuration.max_processing_length)

    @abc.abstractmethod
    def optimize_pipeline(self, pipeline):
        """
        Optimize the given pipeline and return the best found parameters
        This method will be called during the optimization process
        every time a new pipeline has been created.
        It is used to optimize the given pipeline and has to be implemented according
        to the optimization process used.

        :param pipeline: The pipeline description to use for optimization
        :type pipeline: list[str]
        :return: The best parameters found for this pipeline
        :rtype: dict[str, object]
        """
        raise NotImplementedError()

