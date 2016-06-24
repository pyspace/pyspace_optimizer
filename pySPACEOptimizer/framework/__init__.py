import pkg_resources


TASK_ENTRY_POINT = "pySPACEOptimizer.tasks"
OPTIMIZER_ENTRY_POINT = "pySPACEOptimizer.optimizers"


def task_from_yaml(stream):
    """
    :rtype: T <= Task
    """
    import yaml
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
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
    type_ = task_description["type"]
    entry_points = [entry_point for entry_point in pkg_resources.iter_entry_points(TASK_ENTRY_POINT, type_)]
    if len(entry_points) > 1:
        raise RuntimeWarning("More than one entry point found for task type '%s', please check installation.\n"
                             "Taking first entry point and ignoring all others" % type_)
    elif not entry_points:
        raise RuntimeError("No entry point found for task type '%s', please check installation" % type_)
    task = entry_points[0].resolve()(**task_description)
    task.log_task()
    return task


def list_optimizers():
    return [entry_point.name for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT)]


def optimizer_factory(task, backend, best_result_file=None):
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
    type_ = task["optimizer"]
    entry_points = [entry_point for entry_point in pkg_resources.iter_entry_points(OPTIMIZER_ENTRY_POINT, type_)]
    if len(entry_points) > 1:
        raise RuntimeWarning("More than one entry point found for optimizer '%s', please check installation.\n"
                             "Taking first entry point and ignoring all others" % type_)
    elif not entry_points:
        raise RuntimeError("No entry point found for optimizer '%s', please check installation" % type_)
    return entry_points[0].resolve()(task=task, backend=backend, best_result_file=best_result_file)
