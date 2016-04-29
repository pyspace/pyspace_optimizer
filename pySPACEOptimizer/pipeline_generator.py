#!/bin/env python
# -*- coding: utf-8 -*-
import logging
import numpy

from pySPACEOptimizer.tasks.base_task import Task, is_source_node, is_sink_node, get_node_type


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
        self._max_length = configuration["max_pipeline_length"]
        self._source_node = configuration["source_node"]
        self._sink_node = configuration["sink_node"]
        self._sink_node_inputs = configuration.nodes[self._sink_node].get_input_types()
        self._nodes = configuration.weighted_nodes_by_input_type()
        self._required_node_types = configuration.required_node_types
        self._required_nodes = configuration.required_nodes
        self._configuration_nodes = configuration.nodes
        self._configuration = configuration
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

    def _get_output_type(self, node_name, input_type):
        try:
            return self._configuration_nodes[node_name].get_output_type(input_type)
        except TypeError:
            return None

    def _make_pipeline(self, pipeline_array, input_type, pipeline_types, index):
        # First node has to be a "SourceNode", emitting the correct data type
        first_node = False
        if index == 0:
            if self._source_node is None:
                # Automatically select a node
                self._logger.debug("Will select the source node automatically")
                first_node = True
            else:
                # Use the given node
                pipeline_array[index] = self._source_node
                pipeline_types[index] = get_node_type(self._source_node)
                index += 1
                input_type = self._get_output_type(self._source_node, input_type)
                self._logger.debug("Using '%s' as source node and '%s' as input type", self._source_node, input_type)

        optional_nodes = set(pipeline_array[:index]).difference(self._required_nodes)
        optional_slots = self._max_length - len(self._required_nodes)
        if len(optional_nodes) > optional_slots or self._input_type not in self._nodes or index == self._max_length - 1:
            # We have more "optional" nodes, than we can have or we can't process the input type
            # or the pipeline will get too long. Early exit -> raise StopIteration
            self._logger.debug("\t" * index + "No valid pipeline possible! Returning..")
            raise StopIteration()

        for node in self._nodes[input_type]:
            # Append only if:
            # the node is not contained in the pipeline and:
            # - it is the first node and it's a source node
            # - it's not the first node and not a sink or source node
            if node not in pipeline_array[:index]:
                if (first_node and is_source_node(node)) or (
                                not first_node and not is_sink_node(node) and not is_source_node(node)):
                    self._logger.debug("\t" * index + "Appending '%s'", node)
                    pipeline_array[index] = node
                    pipeline_types[index] = get_node_type(node)
                    node_output = self._get_output_type(node, input_type)
                    if node_output is not None:
                        if node_output in self._sink_node_inputs:
                            # Valid Pipeline, append the performance sink node
                            # and yield a list containing exactly the pipeline
                            pipeline_array[index + 1] = self._sink_node
                            pipeline_types[index + 1] = get_node_type(self._sink_node)
                            if self._required_node_types.issubset(pipeline_types[:index + 2]) and \
                                    self._required_nodes.issubset(pipeline_array[:index + 2]):
                                # All required types and nodes are in the pipeline
                                # it might work.. yield it
                                result = list(pipeline_array[:index + 2])
                                self._logger.debug("\t" * index + "Valid pipeline found: '%s'", result)
                                yield result
                            else:
                                self._logger.debug("\t" * index + "Not all types required types contained: %s",
                                                   pipeline_types[:index + 2])
                        # Try to extend the pipeline
                        self._logger.debug("\t" * index + "Using '%s' as new input type", node_output)
                        for pipeline in self._make_pipeline(pipeline_array, node_output, pipeline_types, index + 1):
                            yield pipeline
                    else:
                        self._logger.debug("\t" * index +
                                           "Skipping node '%s' because node  get_output_type returned None" % node)

    def __iter__(self):
        # Generate all pipelines
        for pipeline in self._make_pipeline(numpy.chararray(self._max_length, itemsize=255),
                                            self._input_type,
                                            numpy.chararray(self._max_length, itemsize=255),
                                            index=0):
            yield pipeline
        raise StopIteration()
