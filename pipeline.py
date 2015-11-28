#!/bin/env python
# -*- coding: utf-8 -*-
import inspect
from pySPACE.missions import nodes


class PipelineNode(dict):

    def __init__(self, node_name):
        self.class_ = nodes.DEFAULT_NODE_MAPPING[node_name]
        self.name = node_name
        super(PipelineNode, self).__init__({
            "node": self.name,
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
        if isinstance(other, self.__class__):
            return other.name == self.name
        return False

    def __repr__(self):
        return self.name


class ParameterRangesDict(dict):

    def __init__(self, parameters):
        super(ParameterRangesDict, self).__init__()
        self.__parameters = parameters

    def __setitem__(self, key, value):
        if key not in self.__parameters:
            raise AttributeError("Parameter '%s' not found in the pipeline" % key)
        if not isinstance(value, list):
            raise AttributeError("Only lists of values are supported as parameter ranges")
        super(ParameterRangesDict, self).__setitem__(key, value)


class Pipeline(dict):

    def __init__(self, node_chain, data_set_path):
        """
        Creates a new node with the given `name` and `data_set_path`.
        The pipeline uses the given nodes for processing.

        :param node_chain: A list of node names to create the pipeline with
        :type node_chain: [PySPACEPipelineNode]
        :param data_set_path: The path to the data set to use as input to the pipeline
        :type data_set_path: unicode

        :return: A new PySPACEPipeline with the given name, nodes and data set path
        :rtype: Pipeline
        """
        self.__space = None
        self.pipeline_variables = []
        for node in node_chain:
            for parameter in node.parameter_space.iterkeys():
                self.pipeline_variables.append(parameter)
        super(Pipeline, self).__init__({
            "type": "node_chain",
            "node_chain": node_chain,
            "input_path": data_set_path,
            "parameter_ranges": ParameterRangesDict(self.pipeline_variables)
        })

    @property
    def pipeline_space(self):
        if self.__space is None:
            space = {}
            for node in self["node_chain"]:
                space.update(node.parameter_space)
            self.__space = space
        return self.__space

    def set_parameter(self, parameter_name, value):
        self["parameter_ranges"][parameter_name] = [value]

    @classmethod
    def from_node_list(cls, node_list, data_set_path):
        node_chain = [PipelineNode(node_name) for node_name in node_list]
        return Pipeline(node_chain, data_set_path)
