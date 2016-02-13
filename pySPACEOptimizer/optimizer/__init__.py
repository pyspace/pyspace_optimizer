#!/bin/env python
# -*- coding: utf-8 -*-
import pkg_resources
import logging


OPTIMIZER_ENTRY_POINT = "pySPACEOptimizer.optimizers"
LOGGER = logging.getLogger(__name__)


def list_optimizers():
    return [entry_point.name for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT)]


def optimizer_factory(task, backend="serial", best_result_file="best_result.pickle"):
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
    :param best_result_file: A file-like object to store the found best result to
    :type best_result_file: File
    :return: A new optimizer optimizing the given ``task`` using the given ``backend``.
    :rtype: R <= PySPACEOptimizer
    """
    LOGGER.debug("Creating an optimizer for task '%s' with backend '%s'", task, backend)    
    type_ = task["optimizer"]
    for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT, type_):
        class_ = entry_point.resolve()
        LOGGER.debug("Using Optimizer: %s", class_)
        return entry_point.resolve()(task=task, backend=backend, best_result_file=best_result_file)
