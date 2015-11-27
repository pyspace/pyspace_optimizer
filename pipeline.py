#!/bin/env python
# -*- coding: utf-8 -*-
import inspect
from missions import nodes


class PipelineNode(dict):

    def __init__(self, node_name):
        self.class_ = nodes.DEFAULT_NODE_MAPPING[node_name]
        self.name = node_name
        super(PipelineNode, self).__init__({
            "node": node_name,
            "parameters": {param: self.make_parameter_name(param) for param in self.parameters}
        })
        self.__space = None

    @property
    def parameters(self):
        argspec = inspect.getargspec(self.class_.__init__)
        return [arg for arg in argspec.args if arg != "self"]

    @property
    def parameter_space(self):
        if self.__space is None:
            argspec = inspect.getargspec(self.class_.__init__)
            if argspec.defaults is not None:
                default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
                self.__space = {self.make_parameter_name(param): default for param, default in default_args}
            else:
                self.__space = {}
        return self.__space

    def make_parameter_name(self, parameter):
        return "__{node_name}_{parameter}__".format(
            node_name=self.name,
            parameter=parameter
        )

    def __eq__(self, other):
        return other.name == self.name

    def __repr__(self):
        return self.name


class Pipeline(dict):

    def __init__(self, nodes, data_set_path):
        """
        Creates a new node with the given `name` and `data_set_path`.
        The pipeline uses the given nodes for processing.

        :param nodes: A list of node names to create the pipeline with
        :type nodes: [PySPACEPipelineNode]
        :param data_set_path: The path to the data set to use as input to the pipeline
        :type data_set_path: unicode

        :return: A new PySPACEPipeline with the given name, nodes and data set path
        :rtype: Pipeline
        """
        super(Pipeline, self).__init__({
            "type": "node_chain",
            "node_chain": nodes,
            "input_path": data_set_path,
            "parameter_ranges": {}
        })
        self.__space = None
        self.__variables = None

    @property
    def pipeline_space(self):
        if self.__space is None:
            space = []
            for node in self["node_chain"]:
                space.extend(node.parameter_space)
            self.__space = space
        return self.__space

    @property
    def pipeline_variables(self):
        if self.__variables is None:
            variables = []
            for node in self["node_chain"]:
                for parameter in node.parameter_space:
                    variables.append(parameter.arg)
            self.__variables = variables
        return self.__variables

    def set_parameter(self, parameter_name, value):
        if parameter_name not in self.pipeline_variables:
            raise AttributeError("Parameter '%s' not found in the pipeline" % parameter_name)
        else:
            self["parameter_ranges"][parameter_name] = value

    @classmethod
    def from_node_list(cls, node_list, data_set_path):
        nodes = [PipelineNode(node_name) for node_name in node_list]
        return Pipeline(nodes, data_set_path)
