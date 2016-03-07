#!/bin/env python
# -*- coding: utf-8 -*-
import copy
import logging
import os

import sys
import yaml

import pySPACE
from pySPACEOptimizer.pipelines.nodes import PipelineNode
from pySPACEOptimizer.tasks.base_task import Task
from pySPACEOptimizer.utils import OutputRedirecter

try:
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import SafeDumper as Dumper


class Pipeline(object):

    def __init__(self, configuration, node_chain=None):
        """
        Creates a new node with the given `name` and `data_set_path`.
        The pipeline uses the given nodes for processing.

        :param configuration: The configuration to use for this Pipeline
        :type configuration: Task
        :param node_chain: A list of node names to create the pipeline with
        :type node_chain: [PipelineNode]

        :return: A new PySPACEPipeline with the given name, nodes and data set path
        :rtype: Pipeline
        """
        if node_chain is not None:
            self._nodes = copy.deepcopy(node_chain)
        else:
            self._nodes = []
        self._input_path = configuration["data_set_path"]
        self.configuration = configuration
        self._logger = self.get_logger()
        self._logger.info("{object!s} is {object!r}".format(object=self))

    @property
    def nodes(self):
        return self._nodes

    @property
    def pipeline_space(self):
        """
        Returns the parameter space of the pipeline.
        The parameter space is a dictionary of the parameters used in this pipeline and their ranges.
        This method automatically excludes the first and the last node, as these are normally a source and a sink
        node that should not be optimized at all.

        :return: The domain of the parameters for this pipeline
        :rtype: dict[str, str]
        """
        space = {}
        for node in self._nodes[1:-1]:
            space.update(node.parameter_space())
        return space

    def operation_spec(self, parameter_ranges=None):
        """
        Return the pipeline as an operation specification usable for pySPACE execution.

        :param parameter_ranges: The ranges to let pySPACE select the values for the parameters for.
        :type parameter_ranges: dict[str, list[object]]
        :return: The pipeline specification as a dictionary
        :rtype: dict[str, str]
        """
        if parameter_ranges is None:
            parameter_ranges = {}

        node_chain = [node.as_dictionary() for node in self._nodes]
        operation_spec = {
            "type": "node_chain",
            "input_path": self._input_path,
            "node_chain": node_chain,
            "parameter_ranges": parameter_ranges
        }
        # Due to bad pySPACE YAML-Parsing, we need to modify the output of the yaml dumper for correct format
        dump = yaml.dump(operation_spec, Dumper=Dumper, default_flow_style=False, indent=4)
        lines = []
        for line in dump.split("\n"):
            if line.startswith(" ") or line.startswith("-"):
                lines.append("    " + line)
            else:
                lines.append(line)
        operation_spec["base_file"] = "\n".join(lines)
        return operation_spec

    def execute(self, parameter_ranges=None, backend=u"serial", base_result_dir=None):
        """
        Executes the pipeline using the given backend.

        :param parameter_ranges: The ranges to let pySPACE select the values for the parameters for.
        :type parameter_ranges: dict[str, list[object]]
        :param backend: The backend to use for execution. (Default: serial)
        :type backend: unicode
        :param base_result_dir: The base directory to put the logfiles into.
        :type base_result_dir: unicode
        :return: The path to the results of the pipeline
        :rtype: unicode
        """
        # noinspection PyBroadException
        try:
            backend = pySPACE.create_backend(backend)
            operation = pySPACE.create_operation(self.operation_spec(parameter_ranges=parameter_ranges),
                                                 base_result_dir=base_result_dir)
            with open(os.devnull, "w") as output:
                with OutputRedirecter(std_out=output, std_err=sys.stderr):
                    pySPACE.run_operation(backend, operation)
            return operation.get_output_directory()
        except:
            self._logger.exception("Error in '%s':", self)
            return None

    def __eq__(self, other):
        if hasattr(other, "nodes"):
            for node in self.nodes:
                if node not in other.nodes:
                    return False
            return True
        return False

    def __hash__(self):
        # Hash all nodes and concat them to a string
        s = "".join([unicode(hash(node)) for node in self.nodes])
        # Also append the input_path as it is important for performance
        s += self._input_path
        # Hash the resulting string
        return hash(s)

    def __repr__(self):
        r = "["
        r += ", ".join([repr(node) for node in self._nodes])
        r += "]"
        r += "@{input!s}".format(input=self._input_path)
        return r

    def __str__(self):
        return "Pipeline<{hash!s:>20s}>".format(hash=hash(self))

    def __getstate__(self):
        return {
            "_nodes": self._nodes,
            "configuration": self.configuration,
            "_input_path": self._input_path}

    def get_logger(self):
        return logging.getLogger("{module}.{object}".format(module=self.__class__.__module__, object=self))

    def get_error_logger(self):
        return logging.getLogger("pySPACEOptimizer.pipelines.errors")

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._logger = self.get_logger()
