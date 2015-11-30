#!/bin/env python
# -*- coding: utf-8 -*-
from . import *
from pyspace_base_optimizer import  PySPACEOptimizer

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


def get_optimizer(name):
    return __optimizer[name]


def optimizer(name):
    def wrapper(class_):
        register_optimizer(name, class_)
        return class_
    return wrapper