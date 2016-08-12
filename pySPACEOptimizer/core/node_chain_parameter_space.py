#!/bin/env python
# -*- coding: utf-8 -*-
import copy
import logging
import logging.handlers
import os
import sys

import yaml

import pySPACE
from pySPACEOptimizer.framework.base_task import Task
from pySPACEOptimizer.framework.node_parameter_space import NodeParameterSpace
from pySPACEOptimizer.utils import output_diverter

try:
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import SafeDumper as Dumper


FORMATTER = logging.Formatter(fmt="[%(asctime)s.%(msecs)03d:%(levelname)10s][%(name)s] %(message)s",
                              datefmt="%d.%m.%Y %H:%M:%S")


class NodeChainParameterSpace(object):

    def __init__(self, configuration, node_list):
        """
        Creates a new node with the given `name` and `data_set_path`.
        The pipeline uses the given nodes for processing.

        :param configuration: The configuration to use for this Pipeline
        :type configuration: Task
        :param node_list: A list of node names to create the pipeline with
        :type node_list: list[NodeParameterSpace]

        :return: A new PySPACEPipeline with the given name, nodes and data set path
        :rtype: NodeChainParameterSpace
        """
        self._nodes = copy.deepcopy(node_list)
        self._input_path = configuration["data_set_path"]
        self.configuration = configuration
        self._logger = None
        self._error_logger = None
        # Create the pipeline dir
        if not os.path.isdir(self.base_result_dir):
            os.makedirs(self.base_result_dir)

    def log_pipeline(self):
        # Log the pipeline
        self.logger.info("{object!s} is {object!r}".format(object=self))

    def __patch_logger(self, name, file_name, level):
        logger = logging.getLogger(name)
        file_path = os.path.join(self.base_result_dir, file_name)
        new_handler = logging.FileHandler(file_path)
        new_handler.setLevel(level)
        new_handler.setFormatter(FORMATTER)
        new_handler.set_name(name)
        # add the new handler
        logger.addHandler(new_handler)
        return logger

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

    def unset_parameters(self):
        """
        Returns a dictionary containing the nodes and
        their parameters that have not been set either
        by the nodes or the optimization task.

        The parameters returned by this method need to be set
        by the user in a valid task description to make this
        processing pipeline executable.

        :return: A dict containing the node and parameters without values
        :rtype: dict[NodeParameterSpace, list[str]]
        """
        result = {}
        for node in self._nodes:
            params_without_default = node.parameters_without_value()
            if params_without_default:
                result[node] = params_without_default
        return result

    def operation_spec(self, parameter_settings=None):
        """
        Return the pipeline as an operation specification usable for pySPACE execution.

        :param parameter_settings: The ranges to let pySPACE select the values for the parameters for.
        :type parameter_settings: list[dict[str, object]]
        :return: The pipeline specification as a dictionary
        :rtype: dict[str, str]
        """
        if parameter_settings is None:
            parameter_settings = []

        node_chain = [node.as_dictionary() for node in self._nodes]
        operation_spec = {
            "type": "node_chain",
            "input_path": self._input_path,
            "node_chain": node_chain,
            "parameter_settings": parameter_settings
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

    @property
    def base_result_dir(self):
        pipeline_hash = str(hash(self)).replace("-", "_")
        return os.path.join(self.configuration.base_result_dir, pipeline_hash)

    @property
    def logger(self):
        if self._logger is None:
            self._logger = self.__patch_logger(
                name="pySPACEOptimizer.pipeline.{pipeline}".format(pipeline=self),
                file_name="pipeline_output.pylog",
                level=logging.INFO)
        return self._logger

    @property
    def error_logger(self):
        if self._error_logger is None:
            self._error_logger = self.__patch_logger(
                name="pySPACEOptimizer.pipeline_errors.{pipeline}".format(pipeline=self),
                file_name="pipeline_errors.pylog",
                level=logging.WARNING)
        return self._error_logger

    def create_operation(self, parameter_settings=None):
        """
        Create an operation from this node chain and the given parameter settings.

        This method will create an pySPACE operation from this node chain and
        the given parameter settings.

        :param parameter_settings: The ranges to let pySPACE select the values for the parameters for.
        :type parameter_settings: list[dict[str, object]]
        :return: An operation that can be executed using the execute method.
        """
        return pySPACE.create_operation(self.operation_spec(parameter_settings=parameter_settings),
                                        base_result_dir=self.base_result_dir)

    @staticmethod
    def execute(operation, backend):
        """
        Executes the pipeline using the given backend.

        :param operation: The operation to execute.
                          This operation needs to be created using the `create_operation` method.
        :param backend: The backend to use for the execution.
        :type backend: Backend
        :return: The path to the results of the pipeline
        :rtype: unicode
        """
        with open(os.devnull, "w") as output:
            with output_diverter(std_out=output, std_err=sys.stderr):
                pySPACE.run_operation(backend, operation)

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
        return "NodeChainParameterSpace<{hash!s:>20s}>".format(hash=hash(self))

    def __getstate__(self):
        new_dict = copy.copy(self.__dict__)
        new_dict["_logger"] = None
        new_dict["_error_logger"] = None
        return new_dict
