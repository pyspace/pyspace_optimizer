from pySPACEOptimizer.framework.base_task import Task, is_node_type


def is_classification_task_node(node_name):
    valid_node_types = ["classification", "preprocessing", "postprocessing", "feature_generation", "feature_selection",
                        "spatial_filtering", "type_manipulation", "sink", "source"]
    return any([is_node_type(node_name, type_) for type_ in valid_node_types])


class ClassificationTask(Task):
    def __init__(self, name, input_path, evaluations_per_pass, metric, class_labels, main_class, **kwargs):
        super(ClassificationTask, self).__init__(name=name, input_path=input_path,
                                                 evaluations_per_pass=evaluations_per_pass, metric=metric, **kwargs)
        if not isinstance(class_labels, list):
            raise ValueError("Class labels must be a list of names")
        if main_class not in class_labels:
            raise ValueError("The main class is not defined as a class label")
        self.update({"class_labels": tuple(class_labels),
                     "main_class": main_class})
 
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

    def default_parameters(self, node):
        # :type node: NodeParameterSpace
        result = super(ClassificationTask, self).default_parameters(node)
        if "class_labels" in node.parameters:
            result["class_labels"] = [self["class_labels"]]
        if "classes_labels" in node.parameters:
            result["classes_labels"] = [self["class_labels"]]
        if "erp_class_label" in node.parameters:
            result["erp_class_label"] = [self["main_class"]]
        if "ir_class" in node.parameters:
            result["ir_class"] = [self["main_class"]]
        return result


class ClassificationTaskWithoutScikit(ClassificationTask):
    @property
    def nodes(self):
        nodes = {}
        for node, class_ in super(ClassificationTaskWithoutScikit, self).nodes.iteritems():
            if is_classification_task_node(node):
                nodes[node] = class_
        return nodes
