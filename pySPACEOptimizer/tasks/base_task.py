#!/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import glob
import os
import logging
import pprint

import pySPACE
from pySPACE.missions.nodes import DEFAULT_NODE_MAPPING
from pySPACE.resources.dataset_defs.base import BaseDataset

__all__ = ["Experiment", "is_source_node", "is_splitter_node", "is_sink_node", "get_node_type"]


def get_node_type(node_name):
    return DEFAULT_NODE_MAPPING[node_name].__module__.replace("pySPACE.missions.nodes.", "").split(".")[0]


def is_node_type(node_name, node_type):
    return get_node_type(node_name=node_name) == node_type


def is_source_node(node_name):
    return is_node_type(node_name, "source")


def is_splitter_node(node_name):
    return is_node_type(node_name, "splitter")


def is_sink_node(node_name):
    return is_node_type(node_name, "sink")


class Task(dict):

    def __init__(self, input_path, class_labels, main_class, optimizer="PySPACEOptimizer", max_pipeline_length=3,
                 max_eval_time=0, passes=1, metric="Percent_incorrect", source_node=None,
                 sink_node="PerformanceSinkNode", whitelist=None, blacklist=None, forced_nodes=None, node_weights=None,
                 parameter_ranges=None, **kwargs):

        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        # First do some sanity checks
        if whitelist is not None:
            for node in whitelist:
                if node not in DEFAULT_NODE_MAPPING:
                    raise ValueError("'{node}' from white list is not a node".format(node=node))

        if node_weights is not None:
            for node, weight in node_weights.items():
                if node not in DEFAULT_NODE_MAPPING:
                    raise ValueError("'{node}' from weight dict is not a node".format(node=node))
                elif not isinstance(weight, (int, float)) or weight < 0:
                    raise ValueError("Weight of Node '{node}' from weight dict is not a positive number".format(
                        node=node))

        if not isinstance(class_labels, list):
            raise ValueError("Class labels must be a list of names")

        if main_class not in class_labels:
            raise ValueError("The main class is not defined as a class label")

        if not is_sink_node(sink_node):
            raise ValueError("The node '{node}' is not a sink node".format(node=sink_node))

        super(Task, self).__init__({
            "data_set_path": input_path,
            "max_pipeline_length": max_pipeline_length,
            "source_node": source_node,
            "sink_node": sink_node,
            "optimizer": optimizer,
            "class_labels": tuple(class_labels),
            "main_class": main_class,
            "metric": metric,
            "whitelist": set(whitelist) if whitelist is not None else set(),
            "blacklist": set(blacklist) if blacklist is not None else set(),
            "forced_nodes": set(forced_nodes) if forced_nodes is not None else set(),
            "node_weights": dict(node_weights) if node_weights is not None else dict(),
            "parameter_ranges": parameter_ranges if parameter_ranges is not None else [],
            "max_eval_time": max_eval_time,
            "passes": passes,
        })
        super(Task, self).update(kwargs)

        # Check the source node
        if source_node is not None and (
                not is_source_node(source_node) or
                self.data_set_type not in DEFAULT_NODE_MAPPING[source_node].get_input_types()):
            raise ValueError("'%s' is either not a source node or is not able to emit data type '%s'" % (
                source_node, self.data_set_type))

        self._log_task()

    def _log_task(self):
        format_ = pprint.pformat(self, indent=4)
        self._logger.debug("Task '{task}': {format}".format(task=self, format=format_))

    def __getitem__(self, item):
        if item in self:
            return super(Task, self).__getitem__(item)
        else:
            return None

    def __str__(self):
        return "%s<%s>" % (self.__class__.__name__, self["data_set_path"])

    def __getstate__(self):
        return {key: value for key, value in self.items()}

    def __setstate__(self, state):
        super(Task, self).update(state)

    @staticmethod
    def __valid_node(node_name):
        return all([not is_node_type(node_name, type_) for type_ in ["data_selection", "debug", "meta",
                                                                     "splitter", "visualization"]])

    @property
    def required_nodes(self):
        nodes = set(self["forced_nodes"])
        if self["source_node"]:
            nodes.add(self["source_node"])
        if self["sink_node"]:
            nodes.add(self["sink_node"])
        return nodes

    @property
    def required_node_types(self):
        return {"source", "sink"}

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
                # Append all source nodes
                nodes.update({
                                 node: class_ for node, class_ in DEFAULT_NODE_MAPPING.items() if is_source_node(node)
                                 })
        else:
            nodes = {node: class_ for node, class_ in DEFAULT_NODE_MAPPING.items() if self.__valid_node(node)}

        # remove blacklisted nodes
        if self["blacklist"]:
            for node in self["blacklist"]:
                if node in nodes:
                    del nodes[node]
        # Return all valid nodes
        return nodes

    @property
    def nodes_by_input_type(self):
        """
        Creates a dictionary of nodes, where the key is the input type, that this node can process.

        :return: A dictionary sorted by the type of input the nodes can process.
        :rtype: Dict
        """
        nodes_by_input_type = {}
        for node_name, node in self.nodes.items():
            for input_type in node.get_input_types():
                if input_type not in nodes_by_input_type:
                    nodes_by_input_type[input_type] = []
                nodes_by_input_type[input_type].append(node_name)
        return nodes_by_input_type

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
                raise TypeError("Inconsistent Data sets found: {old_type} != {new_type}".format(
                    old_type=old_data_set_type, new_type=data_set_type))
            old_data_set_type = data_set_type
        if old_data_set_type is None:
            raise AttributeError("No data sets found at '{dir}'".format(dir=data_set_dir))
        return old_data_set_type.title().replace("_", "")

    def weighted_nodes_by_input_type(self):
        weighted_nodes = {}
        for input_type, nodes in self.nodes_by_input_type.items():
            nodes.sort(key=lambda node: self.node_weight(node), reverse=True)
            weighted_nodes[input_type] = nodes
        return weighted_nodes

    def node_weight(self, node):
        if node in self["node_weights"].keys():
            return self["node_weights"][node]
        else:
            # Use the default node weight
            # noinspection PyBroadException
            try:
                count = 0
                for input_type in self.nodes[node].get_input_types():
                    count += len(self.nodes_by_input_type[input_type])
                return 1 / count
            except Exception:
                return 0

    def default_parameters(self, node):
        # :type node: PipelineNode
        definitions = [parameter_range for parameter_range in self["parameter_ranges"]
                       if parameter_range["node"] == node.name]
        if definitions:
            result = definitions[0]["parameters"]
        else:
            result = {}

        if "class_labels" in node.parameters:
            result["class_labels"] = [self["class_labels"]]
        return result
