from pySPACEOptimizer.framework.base_task import Task, is_node_type


def is_regression_task_node(node_name):
    valid_node_types = ["preprocessing", "postprocessing", "feature_generation", "feature_selection",
                        "spatial_filtering", "sink", "source", "regression"]
    return any([is_node_type(node_name, type_) for type_ in valid_node_types])


class RegressionTask(Task):
    def __init__(self, name, input_path, evaluations_per_pass, metric, **kwargs):
        super(RegressionTask, self).__init__(name=name, input_path=input_path,
                                             evaluations_per_pass=evaluations_per_pass, metric=metric, **kwargs)

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

    def default_parameters(self, node):
        # :type node: NodeParameterSpace
        result = super(RegressionTask, self).default_parameters(node)
        if "evaluation_type" in node.parameters:
            result["evaluation_type"] = "regression"
        return result
