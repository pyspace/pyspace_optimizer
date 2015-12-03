#!/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import glob
import os

import yaml

import pySPACE
from optimizer import get_optimizer
from pipelines import SinkNode
from pySPACE.missions.nodes import DEFAULT_NODE_MAPPING
from pySPACE.resources.dataset_defs.base import BaseDataset
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


__all__ = ["Experiment", "is_source_node", "is_splitter_node", "is_sink_node"]


def is_node_type(node_name, node_type):
    return DEFAULT_NODE_MAPPING[node_name].__module__.find("pySPACE.missions.nodes.%s" % node_type) != -1


def is_source_node(node_name):
    return is_node_type(node_name, "source")


def is_splitter_node(node_name):
    return is_node_type(node_name, "splitter")


def is_sink_node(node_name):
    return is_node_type(node_name, "sink")


class Configuration(dict):

    # TODO: Insert a suitable default metric
    def __init__(self, data_set_path, optimizer, class_labels, main_class, max_pipeline_length=3, metric="",
                 source_node=None, sink_node="PerformanceSinkNode", whitelist=None, blacklist=None,
                 force_list=None, node_weights=None, **kwargs):

        # First do some sanity checks
        if whitelist is None:
            whitelist = []
        else:
            for node in whitelist:
                if not node in DEFAULT_NODE_MAPPING:
                    raise AttributeError("'%s' from white list is not a node" % node)

        if blacklist is None:
            blacklist = []

        if force_list is None:
            force_list = []

        if node_weights is None:
            node_weights = {}
        else:
            for node, weight in node_weights.iteritems():
                if not node in DEFAULT_NODE_MAPPING:
                    raise AttributeError("'%s' from weight dict is not a node" % node)
                elif not isinstance(weight, (int, float)) or weight < 0:
                    raise AttributeError("Weight of Node '%s' from weight dict is not a positive number" % node)

        if not isinstance(class_labels, list):
           raise AttributeError("Class labels must be a list of names")

        if main_class not in class_labels:
            raise AttributeError("The main class is not defined as a class label")

        super(Configuration, self).__init__({
            "data_set_path": data_set_path,
            "max_pipeline_length": max_pipeline_length,
            "source_node": source_node,
            "sink_node": SinkNode(sink_node, main_class),
            "optimizer": optimizer,
            "class_labels": class_labels,
            "main_class": main_class,
            "metric": metric,
            "whitelist": whitelist,
            "blacklist": blacklist,
            "force_list": force_list,
            "node_weights": node_weights,
        })
        nodes_by_input_type = {}
        for node_name, node in self.nodes.iteritems():
            for input_type in node.get_input_types():
                if input_type not in nodes_by_input_type:
                    nodes_by_input_type[input_type] = []
                nodes_by_input_type[input_type].append(node_name)
        super(Configuration, self).update({"nodes_by_input_type": nodes_by_input_type})
        super(Configuration, self).update(**kwargs)

        # Check the source node
        if source_node is not None and (
                not is_source_node(source_node) or
                self.data_set_type not in DEFAULT_NODE_MAPPING[source_node].get_input_types()):
            raise AttributeError("'%s' is either not a source node or is not able to emit data type '%s'" % (
                source_node, self.data_set_type))
        # and the sink node
        if not is_sink_node(sink_node):
            raise AttributeError("The node '%s' is not a sink node" % sink_node)

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError("'%s' does not have an attribute '%s'" % (self, item))

    def __setattr__(self, key, value):
        if key in self:
            self[key] = value

    def __setitem__(self, key, value):
        raise RuntimeError("The experiment can't be changed")

    def __repr__(self):
        return "Experiment<%s>" % self.data_set_path

    def __str__(self):
        return repr(self)

    @property
    def nodes(self):
        if self.whitelist:
            # Whitelist of nodes given, use only these nodes
            nodes = {node: DEFAULT_NODE_MAPPING[node] for node in self.whitelist if not is_splitter_node(node)}
            # Append the sink node
            if self.sink_node not in nodes:
                nodes[self.sink_node.name] = DEFAULT_NODE_MAPPING[self.sink_node.name]
            # Append a possible source node or if none, append all source nodes
            if self.source_node is not None and self.source_node not in nodes:
                nodes[self.source_node] = DEFAULT_NODE_MAPPING[self.source_node]
            elif self.source_node is None:
                # Append only non splitter nodes
                nodes.update({node: class_ for node, class_ in DEFAULT_NODE_MAPPING.iteritems() if is_source_node(node)})
            return nodes
        else:
            return {node: class_ for node, class_ in DEFAULT_NODE_MAPPING.iteritems() if not is_splitter_node(node)}

    @property
    def nodes_by_input_type(self):
        """
        Creates a dictionary of nodes, where the key is the input type, that this node can process.

        :return: A dictionary sorted by the type of input the nodes can process.
        :rtype: Dict
        """
        return self.__nodes_by_input_type

    @property
    def data_set_type(self):
        # Determinate the type of the data set
        if not os.path.isabs(self.data_set_path):
            # we need to have an absolut path here, assume it's relative to the storage loation
            data_set_dir = os.path.join(pySPACE.configuration.storage, self.data_set_path)
        else:
            data_set_dir = self.data_set_path
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

    @property
    def optimizer(self):
        return get_optimizer(self["optimizer"])

    def weighted_nodes_by_input_type(self):
        weighted_nodes = {}
        for input_type, nodes in self.nodes_by_input_type.iteritems():
            nodes.sort(key=lambda node: self.node_weight(node), reverse=True)
            weighted_nodes[input_type] = nodes
        return weighted_nodes

    def node_weight(self, node):
        if node in self.node_weights.keys():
            return self.node_weights[node]
        else:
            # Use the default node weight
            try:
                count = 0
                for input_type in self.nodes[node].get_input_types():
                    count += len(self.nodes_by_input_type[input_type])
                return 1 / count
            except Exception:
                return 0

    @classmethod
    def from_yaml(cls, file_path):
        with open(file_path, "rb") as file_:
            values = yaml.load(file_, Loader=Loader)
        return cls(**values)
