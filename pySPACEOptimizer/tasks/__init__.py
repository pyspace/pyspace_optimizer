import pkg_resources

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader



TASK_ENTRY_POINT = "pySPACEOptimizer.tasks"


def task_from_yaml(stream):
    description = yaml.load(stream, Loader=Loader)
    return task_factory(description)


def list_tasks():
    return [entry_point.name for entry_point in pkg_resources.iter_entry_points(TASK_ENTRY_POINT)]


def task_factory(task_description):
    """
    Creates a new task depending on the description of the task.
    The ``task_description`` is a dictionary containing at least an attribute "type"
    which defines the type of task to use.
    To list all possible types of tasks see list_tasks().
    This function returns an object which is a subclass of ``Task``.

    :param task_description: The description of the task to execute as a dictionary
    :type task_description: dict[str, object]
    :return: A new Task-Object corresponding to the given description.
    :rtype: T <= Task
    """
    type = task_description["type"]
    entry_points = [entry_point for entry_point in pkg_resources.iter_entry_points(TASK_ENTRY_POINT, type)]
    if len(entry_points) > 1:
        raise RuntimeWarning("More than one entry point found for task type '%s', please check installation.\n"
                             "Taking first entry point and ignoring all others" % type)
    elif not entry_points:
        raise RuntimeError("No entry point found for task type '%s', please check installation" % type)
    return entry_points[0].resolve()(**task_description)
