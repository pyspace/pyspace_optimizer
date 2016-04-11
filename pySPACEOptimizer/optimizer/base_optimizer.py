#!/bin/env python
# -*- coding: utf-8 -*-
import abc
import logging
import os

import shutil

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

    def _generate_pipelines(self):
        for pipeline in PipelineGenerator(self._task):
            self._logger.debug("Testing Pipeline: %s", pipeline)
            pipeline = Pipeline(configuration=self._task,
                                node_chain=[self._create_node(node_name) for node_name in pipeline])
            if self._task.get("restart_evaluation", False):
                # Delete the old values and start over again
                try:
                    shutil.rmtree(pipeline.base_result_dir)
                    os.makedirs(pipeline.base_result_dir)
                except OSError as exc:
                    pipeline.get_logger().warning("Error while trying to remove the old data: %s", exc)
            yield pipeline

    @abc.abstractmethod
    def _create_node(self, node_name):
        """
        Creates a new node for the given node name.

        :param node_name: The name of the node to create an object for.
        :type node_name: str
        :return: A new node with the given node name.
        :rtype: PipelineNode
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_optimization(self, pipelines, max_evals):
        """
        Do a single evaluation step on all given `pipelines` using `max_evals` evaluations.

        :param pipelines: The pipelines to optimize
        :type pipelines: list[Pipeline]
        :param max_evals: The number of evaluations to do at most.
        :type max_evals: int
        :return: A tuple containing, the loss, the best pipeline and the parameters for this pipeline
        :rtype tuple[float, Pipeline, dict[str, object]]
        """
        raise NotImplementedError()

    def optimize(self):
        """
        Optimize all pipelines and return the best found parameters.
        This method should construct all pipelines available and optimize them.

        :return: The best parameters found for this pipeline
        :rtype: tuple[float, Pipeline, dict[str, object]]
        """
        best = [float("inf"), None, None]

        self._logger.info("Optimizing Pipelines")
        # Get the number of evaluations to make
        max_evaluations = self._task["max_evaluations"]
        passes = self._task["passes"]
        evaluations_per_pass = [(max_evaluations / passes) * pass_ for pass_ in range(1, passes + 1)]
        if evaluations_per_pass[-1] < max_evaluations:
            evaluations_per_pass[-1] = max_evaluations

        pipelines = [pipeline for pipeline in self._generate_pipelines()]

        for pass_, evaluations in enumerate(evaluations_per_pass, start=1):
            self._logger.info("-" * 10 + " Optimization pass: %d / %d " % (pass_, passes) + "-" * 10)
            result = self._do_optimization(pipelines=pipelines, max_evals=evaluations)
            if result[0] < best[0]:
                best = result
            self._logger.debug("Best result of pass %d: %s" % (pass_, best))
            self._logger.info("-" * 10 + " Optimization pass: %d / %d " % (pass_, passes) + "-" * 10)
        self._logger.info("Best result: Pipeline %s with %s at loss %.2f" % (best[1], best[2], best[0]))
        return best
