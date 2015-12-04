#!/bin/env python
# -*- coding: utf-8 -*-
from pyspace_base_optimizer import PySPACEOptimizer
from . import *

__optimizer = {}


def register_optimizer(name, class_):
    global __optimizer
    if name not in __optimizer:
        if issubclass(class_, PySPACEOptimizer):
            __optimizer[name] = class_
        else:
            raise TypeError("'%s' is not a subclass of '%s'" % (class_, PySPACEOptimizer))
    else:
        raise AttributeError("Duplicate name '%s' for optimizers" % name)


def optimizer_factory(configuration, backend="serial"):
    #TODO: Import all submodules to enable the dynamic declaration
    return __optimizer[configuration.optimizer](configuration, backend)


def optimizer(name):
    def wrapper(class_):
        register_optimizer(name, class_)
        return class_
    return wrapper