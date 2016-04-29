#!/bin/env python
# -*- coding: utf-8 -*-
import abc
import logging

from pySPACEOptimizer.optimizer.performance_graphic import PerformanceGraphic
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
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

    PERFORMANCE_GRAPHIC_CLASS = PerformanceGraphic

    def __init__(self, task, backend, best_result_file):
        """
        :type task: Task
        :type backend: str
        :type best_result_file: File
        """
        self._task = task
        self._backend = backend
        if best_result_file is not None:
            self._best_result_file = best_result_file
        else:
            self._best_result_file = "%s_best.yaml" % task["data_set_path"]
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__pipelines = []
        self.__performance_graphic = PerformanceGraphic(window_size=task["window_size"])
        self.__performance_graphic.start()

    @property
    def logger(self):
        return self._logger

    def _performance_graphic_add(self, pipeline, id_, loss):
        self.__performance_graphic.add(pipeline, id_, loss)

    def _performance_graphic_update(self):
        self.__performance_graphic.update()

    def _store_best_result(self, best_pipeline, best_parameters):
        """
        :type best_pipeline: Pipeline
        :type best_parameters: dict[str, list[object]]
        """
        parameter_ranges = {param: [value] for param, value in best_parameters.iteritems()}
        operation_spec = best_pipeline.operation_spec(parameter_ranges=parameter_ranges)
        with open(self._best_result_file, "wb") as best_result_file:
            # Write the result to the object
            best_result_file.write(operation_spec["base_file"])

    def _generate_pipelines(self):
        if not self.__pipelines:
            for node_chain in PipelineGenerator(self._task):
                self._logger.debug("Testing Pipeline: %s", node_chain)
                pipeline = Pipeline(configuration=self._task,
                                    node_chain=[self._create_node(node) for node in node_chain])
                self.__pipelines.append(pipeline)
                yield pipeline
        else:
            for pipeline in self.__pipelines:
                yield pipeline

    @abc.abstractmethod
    def _create_node(self, node_name):
        raise NotImplementedError()

    @abc.abstractmethod
    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.

        :return: The best parameters found for this pipeline
        :rtype: tuple[float, Pipeline, dict[str, object]]
        """
        raise NotImplementedError()

    def __del__(self):
        self.__performance_graphic.stop()
        self.__performance_graphic.join()
