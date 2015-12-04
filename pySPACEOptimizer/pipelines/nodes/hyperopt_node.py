#!/bin/env python
# -*- coding: utf-8 -*-
from pySPACEOptimizer.pipelines.nodes import PipelineNode, PipelineSinkNode, PipelineSourceNode
from hyperopt import hp


class HyperoptNode(PipelineNode):

    def __init__(self, node_name, configuration):
        super(HyperoptNode, self).__init__(node_name=node_name, configuration=configuration)

    @property
    def parameter_space(self):
        space = {}
        for key, value in super(HyperoptNode, self).parameter_space.iteritems():
            if isinstance(value, dict):
                # Dict objects represent a distribution
                if all(x in value.keys() for x in ["mu", "sigma"]):
                    if "type" in value and value["type"] == "int":
                        # Integer distribution, use qlognormal
                        space[key] = hp.qlognormal(key, value["mu"], value["sigma"], value["q"])
                    else:
                        # (Log-)normal distribution
                        space[key] = hp.lognormal(key, value["mu"], value["sigma"])
                elif all(x in value.keys() for x in ["min", "max"]):
                    # Uniform distribution
                    if "type" in value and value["type"] == "int":
                        space[key] = hp.qloguniform(key, value["min"], value["max"], value["q"])
                    else:
                        space[key] = hp.loguniform(key, value["min"], value["max"])
            else:
                # Create a choice with the value
                space[key] = hp.choice(key, value)
        return space


class HyperoptSinkNode(PipelineSinkNode):
    pass


class HyperoptSourceNode(PipelineSourceNode):
    pass
