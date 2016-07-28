#!/bin/env python
# -*- coding: utf-8 -*-
import abc
import logging
import os
import sys
import threading
from multiprocessing import Manager

from pySPACE.tools.progressbar import ProgressBar, Percentage, Bar, ETA
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

    class QueueReader(threading.Thread):
        SENTINEL_VALUE = None

        def __init__(self, task, optimizer):
            super(PySPACEOptimizer.QueueReader, self).__init__(name="QueueReader")
            self.__optimizer = optimizer
            self.__evaluations = task["evaluations_per_pass"]
            self.__passes = task["passes"]
            self.__progress_bar = ProgressBar(widgets=['Progress: ', Percentage(), ' ', Bar(), ' ', ETA()],
                                              maxval=self.__evaluations * self.__passes, fd=sys.stdout)

        def set_number_of_pipelines(self, number_of_pipelines):
            self.__progress_bar.maxval = self.__evaluations * self.__passes * number_of_pipelines

        def run(self):
            self.__progress_bar.update(0)
            while True:
                result = self.__optimizer.queue.get()
                if result != self.SENTINEL_VALUE:
                    id_, loss, pipeline, parameters = result
                    self.__optimizer.logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s",
                                                  pipeline, loss, parameters)
                    if loss <= self.__optimizer.best[0]:
                        self.__optimizer.best = [loss, pipeline, parameters]
                        self.__optimizer.store_best_result(best_pipeline=pipeline,
                                                           best_parameters=parameters)
                    # Update the progress bar
                    self.__progress_bar.update(self.__progress_bar.currval + 1)
                    # Update the performance graphic
                    self.__optimizer.performance_graphic_add(pipeline, id_, loss)
                else:
                    # Sentinel means no more values - break
                    break

        def stop(self):
            self.__optimizer.queue.put(PySPACEOptimizer.QueueReader.SENTINEL_VALUE)

    def __init__(self, task, backend, best_result_file):
        """
        :type task: Task
        :type backend: str
        :type best_result_file: File
        """
        self._task = task
        self._backend = backend
        if best_result_file is not None:
            self.__best_result_file = best_result_file
        else:
            self.__best_result_file = "%s_best.yaml" % task["data_set_path"]
        self.__logger = logging.getLogger("pySPACEOptimizer.optimizer.{optimizer}".format(optimizer=self))
        self.__pipelines = []
        # Calculate the queue size as beeing large enough
        # to store the results of all evaluations
        # of all pipelines beein processed in parallel
        self.__queue = Manager().Queue(maxsize=task["max_parallel_pipelines"] * task["evaluations_per_pass"] * task["passes"])
        self.__performance_graphic = PerformanceGraphic(file_path=os.path.join(task.base_result_dir, "performance.pdf"))
        self.__queue_reader = PySPACEOptimizer.QueueReader(task, self)
        self.__best = [float("inf"), None, None]

    @property
    def logger(self):
        return self.__logger

    @property
    def queue(self):
        return self.__queue

    @property
    def best(self):
        return self.__best

    @best.setter
    def best(self, best_values):
        self.__best = best_values

    def performance_graphic_add(self, pipeline, id_, loss):
        self.__performance_graphic.add(pipeline, id_, loss)

    def store_best_result(self, best_pipeline, best_parameters):
        """
        :type best_pipeline: NodeChainParameterSpace
        :type best_parameters: dict[str, object]
        """
        operation_spec = best_pipeline.operation_spec(parameter_settings=[best_parameters])
        with open(self.__best_result_file, "wb") as best_result_file:
            # Write the result to the object
            best_result_file.write(operation_spec["base_file"])

    def _generate_node_chain_parameter_spaces(self):
        if not self.__pipelines:
            for node_list in NodeListGenerator(self._task):
                self.logger.debug("Testing NodeChainParameterSpace: %s", node_list)
                pipeline = NodeChainParameterSpace(configuration=self._task,
                                                   node_list=[self._create_node(node) for node in node_list])
                self.__pipelines.append(pipeline)
                self.__queue_reader.set_number_of_pipelines(len(self.__pipelines))
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
        self.__queue_reader.start()
        try:
            self.optimize()
        finally:
            self.__queue_reader.stop()
            self.__queue_reader.join()
            self.__performance_graphic.stop()
            self.__performance_graphic.join()
        return self.best

    @abc.abstractmethod
    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.
        """
        raise NotImplementedError()
