#!/bin/env python
# -*- coding: utf-8 -*-
import inspect
from hyperopt import hp
from pySPACE.missions.nodes import DEFAULT_NODE_MAPPING


class Node(object):
    def __init__(self, node_name):
        self.name = node_name
        self.class_ = DEFAULT_NODE_MAPPING[node_name]

    @property
    def parameter_space(self):
        argspec = inspect.getargspec(self.class_.__init__)
        default_args = zip(argspec.args[-len(argspec.defaults):],
                           argspec.defaults)
        return [
            hp.lognormal(self.__make_parameter_name(arg), default, 1))
            for arg, default in default_args
        ]
    
    def __make_parameter_name(self, parameter):
        return "__{node_name}_{parameter}__".format(
            node_name=self.name,
            parameter=parameter
        )

    @property
    def parameters(self):
        argspec = inspect.getargspec(self.class_.__init__)
        return argspec.args
    
    def as_dict(self):
        return {
            "node": node_name,
            "parameters": {
                param: self.__make_parameter_name(param)
                    for param in self.parameters
            }
        }


class PipelineGenerator(object):

    @staticmethod
    def create_nodes_by_input_type():
        nodes_by_input_type = {}
        for node_name, node in DEFAULT_NODE_MAPPING.iteritems():
            for input_type in node.get_input_types():
                if input_type not in nodes_by_input_type:
                    nodes_by_input_type[input_type] = []
                nodes_by_input_type[input_type].append(node_name)
        return nodes_by_input_type
    
    @staticmethod
    def create_input_output_types_for_nodes():
        nodes = {}
        for node_name, node in DEFAULT_NODE_MAPPING.iteritems():
            output = []
            for input_type in node.get_input_types():
                output.append(node.get_output_type(input_type))
            nodes[node_name] = output
        return nodes
    
    def __init__(self, dataset_type, max_length):
        self.__nodes = self.create_nodes_by_input_type()
        self.__inout = self.create_input_output_types_for_nodes()
        self.__input_type = dataset_type
        self.__max_length = max_length

    def __make_pipeline(self, input_types, pipeline):
        if len(pipeline) == self.__max_length:
            return
        for input_type in input_types:
            for node in self.__nodes[input_type]:
                pipeline.append(Node(node))
                self.__make_pipeline(self.__output[node], pipeline)

    def __iter__(self):
        if self.__input_type in self.__nodes:
            current_pipeline = []
            while self.__nodes[self.__input_type]:
                if current_pipeline:
                    # We did already generate a pipeline, simply pop the
                    # last element and take new one
                    current_pipeline.pop()
                    node = current_pipeline[-1]
                    input_types = self.__output[node.name]
                else:
                    input_types = [self.__input_type]
                self.__make_pipeline(input_types, current_pipeline)
                # TODO: Check if the pipeline does make any sense
                yield current_pipeline
        raise StopIteration()
