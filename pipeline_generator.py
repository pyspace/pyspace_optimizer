#!/bin/env python
# -*- coding: utf-8 -*-
import inspect

from pipeline import Pipeline
from pySPACE.missions import nodes


class PipelineGenerator(object):

    def __init__(self, dataset_type, max_length, performance_node="PerformanceSinkNode"):
        """
        Creates a new pipeline generator.
        This generator will create all pipelines that are able to process
        the data with the given `dataset_type` and that have at most `max_length` elements.

        :param dataset_type: The type of the dataset. This will be used as the input to the first node
        :type dataset_type: basestring
        :param max_length: The maximal length of the pipline in number of nodes
        :type max_length: int

        :return: A new pipeline generator generating all pipelines able to process the given dataset type.
        :rtype: PipelineGenerator
        """
        self.__input_type = dataset_type
        self.__max_length = max_length - 1
        self.__performanceNode = performance_node
        self.__performanceNode_inputs = nodes.DEFAULT_NODE_MAPPING[performance_node].get_input_types()
        self.__nodes = self.create_nodes_by_input_type()

    def create_nodes_by_input_type(self):
        """
        Creates a dictionary of nodes, where the key is the input type, that this node can process.

        :return: A dictionary sorted by the type of input the nodes can process.
        :rtype: Dict
        """
        nodes_by_input_type = {}
        for node_name, node in nodes.DEFAULT_NODE_MAPPING.iteritems():
            for input_type in node.get_input_types():
                if input_type not in nodes_by_input_type:
                    nodes_by_input_type[input_type] = []
                nodes_by_input_type[input_type].append(node_name)
        return nodes_by_input_type

    @staticmethod
    def __get_output_type(node_name, input_type):
        return nodes.DEFAULT_NODE_MAPPING[node_name].get_output_type(input_type)

    def __make_pipeline(self, pipeline, input_type):
        if len(pipeline) == self.__max_length or self.__input_type not in self.__nodes:
            # The pipeline get's to long or we got an input type we can't process.
            # Raise an exception.
            raise StopIteration()
        for node in self.__nodes[input_type]:
            if node not in pipeline:
                pipeline.append(node)
                try:
                    node_output = self.__get_output_type(node, input_type)
                    if node_output not in self.__performanceNode_inputs:
                        for pipeline in self.__make_pipeline(pipeline, node_output):
                            yield pipeline
                    else:
                        # Valid Pipeline, append the performance sink node, yield it,
                        # nd pop the last element for next pipeline
                        pipeline.append(self.__performanceNode)
                        yield pipeline
                        # Pop the performance sink node
                        pipeline.pop()
                except Exception:
                    # No valid pipeline found
                    pass
                # Pop the last element
                pipeline.pop()

    def __iter__(self):
        for pipeline in self.__make_pipeline([], self.__input_type):
            yield pipeline
        raise StopIteration()
