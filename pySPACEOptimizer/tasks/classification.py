from pySPACEOptimizer.tasks.base_task import Task, is_node_type


def is_classification_task_node(node_name):
    valid_node_types = ["classification", "preprocessing", "postprocessing", "feature_generation", "feature_selection",
                        "spatial_filtering", "type_manipulation", "sink", "source"]
    return any([is_node_type(node_name, type_) for type_ in valid_node_types])


class ClassificationTask(Task):    

    @property
    def required_node_types(self):
        node_types = super(ClassificationTask, self).required_node_types
        node_types.add("classification")
        return node_types

    @property
    def nodes(self):
        nodes = {}
        for node, class_ in super(ClassificationTask, self).nodes.iteritems():
            if is_classification_task_node(node):
                nodes[node] = class_
            elif is_node_type(node, "scikits_node") and \
                    any([node.lower().find(type_) != -1 for type_ in ["classifier"]]):
                nodes[node] = class_
        return nodes


class ClassificationTaskWithoutScikit(Task):
    @property
    def nodes(self):
        nodes = {}
        for node, class_ in super(ClassificationTaskWithoutScikit, self).nodes.iteritems():
            if is_classification_task_node(node):
                nodes[node] = class_
        return nodes
