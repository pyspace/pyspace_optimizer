from pySPACEOptimizer.framework.base_task import Task, is_node_type


def is_regression_task_node(node_name):
    valid_node_types = ["preprocessing", "postprocessing", "feature_generation", "feature_selection",
                        "spatial_filtering", "sink", "source", "regression"]
    return any([is_node_type(node_name, type_) for type_ in valid_node_types])


class RegressionTask(Task):
    def __init__(self, name, input_path, evaluations_per_pass, **kwargs):
        super(RegressionTask, self).__init__(name, input_path, evaluations_per_pass, **kwargs)

    @property
    def required_node_types(self):
        node_types = super(RegressionTask, self).required_node_types
        node_types.add("regression")
        return node_types

    @property
    def nodes(self):
        nodes = {}
        for node, class_ in super(RegressionTask, self).nodes.iteritems():
            if is_regression_task_node(node):
                nodes[node] = class_
        return nodes

