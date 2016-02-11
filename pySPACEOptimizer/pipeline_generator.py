#!/bin/env python
# -*- coding: utf-8 -*-
import numpy
from pySPACEOptimizer.tasks.base_task import Task, is_source_node, is_splitter_node, is_sink_node, get_node_type


class PipelineGenerator(object):

    def __init__(self, configuration):
        """
        Creates a new pipeline generator.
        This generator will create all pipelines that are able to process
        the data with the data set type from the given `configuration` and that are have at most `max_processing_length`
        variable elements.
        Additionally to these elements every pipeline will have a SourceNode, a SplitterNode and a SinkNode.
        The source and splitter nodes can be given by the configuration or determined dynamically by the generator.

        :param configuration: The configuration for this experiment to use for pipeline generation.
        :type configuration: Task
        :return: A new pipeline generator generating all pipelines able to process the given data set type.
        :rtype: PipelineGenerator
        """
        self._input_type = configuration.data_set_type
        # We always need to have a emitter, a splitter and a sink, therefore there must be at least 3 nodes
        # But we don't count the sink node, therefor only add 2
        self._max_length = configuration["max_pipeline_length"] - 1
        self._source_node = configuration["source_node"]
        self._sink_node = configuration["sink_node"]
        self._sink_node_inputs = configuration.nodes[self._sink_node].get_input_types()
        self._nodes = configuration.weighted_nodes_by_input_type()
        self._required_nodes = set(configuration.required_node_types)
        self._configuration = configuration

    def _get_output_type(self, node_name, input_type):
        try:
            return self._configuration.nodes[node_name].get_output_type(input_type)
        except TypeError:
            return None

    def _make_pipeline(self, pipeline, input_type, pipeline_types, index):
        # First node has to be a "SourceNode", emitting the correct data type
        first_node = False
        if index == 0:
            if self._source_node is None:
                # Automatically select a node
                first_node = True
            else:
                # Use the given node
                pipeline[index] = self._source_node
                input_type = self._get_output_type(self._source_node, input_type)

        if index == self._max_length or self._input_type not in self._nodes:
            # The pipeline get's to long or we got an input type we can't process.
            # Raise an exception.
            raise StopIteration()

        for node in self._nodes[input_type]:
            # Append only if:
            # - it is the first node and it's a source node
            # - it's not the first node and not a splitter node and the type is not contained in the pipeline
            if (first_node and is_source_node(node)) or (
                            not first_node and
                            not is_splitter_node(node) and
                            not is_sink_node(node) and
                            get_node_type(node) not in pipeline_types):
                if node not in pipeline:
                    pipeline[index] = node
                    pipeline_types[index] = get_node_type(node)
                    node_output = self._get_output_type(node, input_type)
                    if node_output not in self._sink_node_inputs:
                        for pipeline in self._make_pipeline(pipeline, node_output, pipeline_types, index + 1):
                            yield pipeline
                    else:
                        # Valid Pipeline, append the performance sink node
                        # and yield a list containing exactly the pipeline
                        pipeline[index + 1] = self._sink_node
                        pipeline_types[index + 1] = get_node_type(self._sink_node)
                        if self._required_nodes.issubset(pipeline_types):
                            # All required types are in the pipeline
                            # it might work.. yield it
                            yield list(pipeline[:index + 2])

    def __iter__(self):
        # Generate all pipelines
        pipeline_array = numpy.chararray(self._max_length + 1, itemsize=255)
        pipeline_types = numpy.chararray(self._max_length + 1, itemsize=255)
        for pipeline in self._make_pipeline(pipeline_array, self._input_type, pipeline_types, 0):
            yield pipeline
        raise StopIteration()
