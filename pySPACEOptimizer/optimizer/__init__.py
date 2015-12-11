#!/bin/env python
# -*- coding: utf-8 -*-
import pkg_resources


OPTIMIZER_ENTRY_POINT = "pySPACEOptimizer.optimizers"




def list_optimizers():
    return [entry_point.name for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT)]


def optimizer_factory(task, backend="serial"):
    """
    Creates a new optimizer using the given ``task`` and ``backend``.
    The ``task`` has to have at least the key `optimizer` which defines the type
    of optimizer to use.
    The ``backend`` defines which pySPACE backend should be used during the execution.

    :param task: The task to execute with this optimizer.
    :type task: T <= Task
    :param backend: The pySPACE backend to use.
                    Possible values are "serial", "mcore", "mpi", "loadl" (Default: "serial")
    :type backend: str
    :return: A new optimizer optimizing the given ``task`` using the given ``backend``.
    :rtype: R <= PySPACEOptimizer
    """
    type_ = task["optimizer"]
    for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT, type_):
        return entry_point.resolve()(task=task, backend=backend)
