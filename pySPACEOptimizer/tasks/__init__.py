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


def task_factory(task_description):
    type = task_description["type"]
    for entry_point in pkg_resources.iter_entry_points(TASK_ENTRY_POINT, type):
        # Import the corresponding object
        entry_point.load()
        # And create an object of it
        return entry_point(task_description)
