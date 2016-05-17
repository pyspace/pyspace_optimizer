#!/bin/env python
# -*- coding: utf-8 -*-
import abc
import logging
import os

from pySPACEOptimizer.core.node_chain_parameter_space import NodeChainParameterSpace
from pySPACEOptimizer.core.nodelist_generator import NodeListGenerator
from pySPACEOptimizer.core.performance_graphic import PerformanceGraphic

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
        self.__performance_graphic = PerformanceGraphic(window_size=task["window_size"],
                                                        file_path=os.path.join(task.base_result_dir, "performance.pdf"))

    @property
    def logger(self):
        return self._logger

    def _performance_graphic_add(self, pipeline, id_, loss):
        self.__performance_graphic.add(pipeline, id_, loss)

    def _store_best_result(self, best_pipeline, best_parameters):
        """
        :type best_pipeline: NodeChainParameterSpace
        :type best_parameters: dict[str, object]
        """
        operation_spec = best_pipeline.operation_spec(parameter_settings=[best_parameters])
        with open(self._best_result_file, "wb") as best_result_file:
            # Write the result to the object
            best_result_file.write(operation_spec["base_file"])

    def _generate_node_chain_parameter_spaces(self):
        if not self.__pipelines:
            for node_list in NodeListGenerator(self._task):
                self._logger.debug("Testing NodeChainParameterSpace: %s", node_list)
                pipeline = NodeChainParameterSpace(configuration=self._task,
                                                   node_list=[self._create_node(node) for node in node_list])
                self.__pipelines.append(pipeline)
                yield pipeline
        else:
            for pipeline in self.__pipelines:
                yield pipeline

    @abc.abstractmethod
    def _create_node(self, node_name):
        """
        Instantiate a concrete NodeParameterSpace instance for the node with the given `node_name`.
        This has to be implemented by a subclass to instantiate it's concrete NodeParameterSpace subclass.

        :param node_name: The name of the node to instantiate
        :type node_name: str
        :return: A NodeParameterSpace instance for the given node name
        :rtype: R <= NodeParameterSpace
        """
        raise NotImplementedError()

    def do_optimization(self):
        self.__performance_graphic.start()
        try:
            return self.optimize()
        finally:
            self.__performance_graphic.stop()
            self.__performance_graphic.join()

    @abc.abstractmethod
    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.

        :return: The best parameters found for this pipeline
        :rtype: tuple[float, NodeChainParameterSpace, dict[str, object]]
        """
        raise NotImplementedError()
