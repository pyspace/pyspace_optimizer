#!/bin/env python
# -*- coding: utf-8 -*-
import uuid
from . import Pipeline, PipelineNode
from hyperopt import hp


class HyperoptPipelineNode(PipelineNode):

    def __init__(self, node_name, uuid_=None):
        if uuid_ is None:
            uuid_ = uuid.uuid4()
        self.__uuid = uuid_
        super(HyperoptPipelineNode, self).__init__(node_name)

    def _make_parameter_name(self, parameter):
        return "__{uuid}_{node_name}_{parameter}__".format(
            uuid=self.__uuid.get_hex(),
            node_name=self.name,
            parameter=parameter
        )

    @property
    def parameter_space(self):
        space = {}
        for key, value in super(HyperoptPipelineNode, self).parameter_space.iteritems():
            if isinstance(value, bool):
                # For boolean parameters create a choice between true and false
                space[key] = hp.choice(key, [True, False])
            elif isinstance(value, (int, float)):
                # For numeric parameters create a normal distribution around default with sigma=1
                space[key] = hp.lognormal(key, value, 1)
            else:
                # Create a choice with only one value
                space[key] = hp.choice(key, [value])
        return space


class HyperoptPipeline(Pipeline):

    @classmethod
    def from_node_list(cls, node_list, data_set_path):
        nodes = [HyperoptPipelineNode(node) for node in node_list]
        return HyperoptPipeline(nodes, data_set_path)
