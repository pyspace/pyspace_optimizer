#!/bin/env python
# -*- coding: utf-8 -*-
import pkg_resources


OPTIMIZER_ENTRY_POINT = "pySPACEOptimizer.optimizers"


def optimizer_factory(task_description, backend="serial"):
    type_ = task_description["optimizer"]
    for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT, type_):
        # Import the corresponding object
        entry_point.load()
        # And create an object of it
        return entry_point(task_description, backend)
