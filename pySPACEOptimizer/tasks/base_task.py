#!/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
import glob
import os
import pySPACE
from pySPACE.missions.nodes import DEFAULT_NODE_MAPPING
from pySPACE.resources.dataset_defs.base import BaseDataset


__all__ = ["Experiment", "is_source_node", "is_splitter_node", "is_sink_node"]


def is_node_type(node_name, node_type):
    return DEFAULT_NODE_MAPPING[node_name].__module__.find("pySPACE.missions.nodes.%s" % node_type) != -1


def is_source_node(node_name):
    return is_node_type(node_name, "source")


def is_splitter_node(node_name):
    return is_node_type(node_name, "splitter")


def is_sink_node(node_name):
    return is_node_type(node_name, "sink")


class Task(dict):

    def __init__(self, input_path, optimizer, class_labels, main_class, max_pipeline_length=3, max_eval_time=60,
                 metric="Percent_incorrect", source_node=None, sink_node="PerformanceSinkNode", whitelist=None, blacklist=None,
                 force_list=None, node_weights=None, parameter_ranges=None, **kwargs):

        # First do some sanity checks
        if whitelist is None:
            whitelist = []
        else:
            for node in whitelist:
                if not node in DEFAULT_NODE_MAPPING:
                    raise ValueError("'%s' from white list is not a node" % node)

        if node_weights is None:
            node_weights = {}
        else:
            for node, weight in node_weights.iteritems():
                if not node in DEFAULT_NODE_MAPPING:
                    raise ValueError("'%s' from weight dict is not a node" % node)
                elif not isinstance(weight, (int, float)) or weight < 0:
                    raise ValueError("Weight of Node '%s' from weight dict is not a positive number" % node)

        if not isinstance(class_labels, list):
            raise ValueError("Class labels must be a list of names")

        if main_class not in class_labels:
            raise ValueError("The main class is not defined as a class label")

        super(Task, self).__init__({
            "data_set_path": input_path,
            "max_pipeline_length": max_pipeline_length,
            "source_node": source_node,
            "sink_node": sink_node,
            "optimizer": optimizer,
            "class_labels": class_labels,
            "main_class": main_class,
            "metric": metric,
            "whitelist": whitelist,
            "blacklist": blacklist if blacklist is not None else [],
            "force_list": force_list if force_list is not None else [],
            "node_weights": node_weights,
            "parameter_ranges": parameter_ranges if parameter_ranges is not None else [],
            "max_eval_time": max_eval_time,
        })
        super(Task, self).update(kwargs)

        # Check the source node
        if source_node is not None and (
                not is_source_node(source_node) or
                self.data_set_type not in DEFAULT_NODE_MAPPING[source_node].get_input_types()):
            raise ValueError("'%s' is either not a source node or is not able to emit data type '%s'" % (
                source_node, self.data_set_type))
        # and the sink node
        if not is_sink_node(sink_node):
            raise ValueError("The node '%s' is not a sink node" % sink_node)

        nodes_by_input_type = {}
        for node_name, node in self.nodes.iteritems():
            for input_type in node.get_input_types():
                if input_type not in nodes_by_input_type:
                    nodes_by_input_type[input_type] = []
                nodes_by_input_type[input_type].append(node_name)
        super(Task, self).__setitem__("nodes_by_input_type", nodes_by_input_type)

    def __str__(self):
        return "Task<%s>" % self["data_set_path"]

    @staticmethod
    def __valid_node(node_name):
        return not is_splitter_node(node_name) and not is_node_type(node_name, "meta")

    @property
    def nodes(self):
        if self["whitelist"]:
            # Whitelist of nodes given, use only these nodes
            nodes = {node: DEFAULT_NODE_MAPPING[node] for node in self["whitelist"] if self.__valid_node(node)}
            # Append the sink node
            if self["sink_node"] not in nodes:
                nodes[self["sink_node"]] = DEFAULT_NODE_MAPPING[self["sink_node"]]
            # Append a possible source node or if none, append all source nodes
            if self["source_node"] is not None and self["source_node"] not in nodes:
                nodes[self["source_node"]] = DEFAULT_NODE_MAPPING[self["source_node"]]
            elif self["source_node"] is None:
                # Append only non splitter nodes
                nodes.update({
                    node: class_ for node, class_ in DEFAULT_NODE_MAPPING.iteritems() if is_source_node(node)
                })
            return nodes
        else:
            return {node: class_ for node, class_ in DEFAULT_NODE_MAPPING.iteritems() if self.__valid_node(node)}

    @property
    def nodes_by_input_type(self):
        """
        Creates a dictionary of nodes, where the key is the input type, that this node can process.

        :return: A dictionary sorted by the type of input the nodes can process.
        :rtype: Dict
        """
        return self["nodes_by_input_type"]

    @property
    def data_set_type(self):
        # Determinate the type of the data set
        if not os.path.isabs(self["data_set_path"]):
            # we need to have an absolut path here, assume it's relative to the storage loation
            data_set_dir = os.path.join(pySPACE.configuration.storage, self["data_set_path"])
        else:
            data_set_dir = self["data_set_path"]
        data_set_dir = os.path.join(data_set_dir, "*", "")
        old_data_set_type = None
        for file_ in glob.glob(data_set_dir):
            data_set_type = BaseDataset.load_meta_data(file_)["type"]
            if old_data_set_type is not None and data_set_type != old_data_set_type:
                raise TypeError("Inconsistent Data sets found: %s != %s" % (old_data_set_type, data_set_type))
            old_data_set_type = data_set_type
        if old_data_set_type is None:
            raise AttributeError("No data sets found at '%s'" % data_set_dir)
        return old_data_set_type.title().replace("_", "")

    def weighted_nodes_by_input_type(self):
        weighted_nodes = {}
        for input_type, nodes in self.nodes_by_input_type.iteritems():
            nodes.sort(key=lambda node: self.node_weight(node), reverse=True)
            weighted_nodes[input_type] = nodes
        return weighted_nodes

    def node_weight(self, node):
        if node in self["node_weights"].keys():
            return self["node_weights"][node]
        else:
            # Use the default node weight
            try:
                count = 0
                for input_type in self.nodes[node].get_input_types():
                    count += len(self.nodes_by_input_type[input_type])
                return 1 / count
            except Exception:
                return 0

    def default_parameters(self, node_name):
        definitions = [parameter_range for parameter_range in self["parameter_ranges"]
                       if parameter_range["node"] == node_name]
        if definitions:
            result = definitions[0]["parameters"]
        else:
            result = {}
        result["class_labels"] = [self["class_labels"]]
        return result