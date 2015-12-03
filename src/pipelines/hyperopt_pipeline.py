#!/bin/env python
# -*- coding: utf-8 -*-
from . import Pipeline, PipelineNode
from hyperopt import hp


class HyperoptPipelineNode(PipelineNode):

    def __init__(self, node_name):
        super(HyperoptPipelineNode, self).__init__(node_name)

    @property
    def parameter_space(self):
        space = {}
        for key, value in super(HyperoptPipelineNode, self).parameter_space.iteritems():
            if isinstance(value, bool):
                # For boolean parameters create a choice between true and false
                space[key] = hp.choice(key, [True, False])
            elif isinstance(value, float):
                # FIXME: inf ist often used as a parameter for an unbound integer interval sample from a large range
                if value == float("inf"):
                    space[key] = hp.randint(key, 10**10)
                else:
                    # For numeric parameters create a normal distribution around default with sigma=1
                    space[key] = hp.lognormal(key, value, 1)
            elif isinstance(value, int):
                space[key] = hp.qlognormal(key, value, 1, 1)
            else:
                # Create a choice with only one value
                space[key] = hp.choice(key, [value])
        return space


class HyperoptPipeline(Pipeline):

    def __init__(self, configuration, node_chain=None):
        super(HyperoptPipeline, self).__init__(configuration=configuration, node_chain=node_chain)
        self._node_class = HyperoptPipelineNode
