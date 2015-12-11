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
    for entry_point in pkg_resources.iter_entry_points(TASK_ENTRY_POINT, type):
        return entry_point.resolve()(**task_description)
