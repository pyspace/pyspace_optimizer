import copy
import inspect

from pySPACE.missions import nodes
from pySPACE.missions.nodes.decorators import PARAMETER_ATTRIBUTE, ChoiceParameter, NormalParameter, QNormalParameter, \
    BooleanParameter


class PipelineNode(object):

    def __init__(self, node_name, task):
        """
        Creates a new node for a pipeline using the given pySPACE node name.

        :param node_name: The name of the node to create a pipeline element for.
        :type node_name: str
        :param task: The task to execute with the pipeline this node is used in
        :type task: T <= Task
        :return: A new pipeline element wrapping the given pySPACE node.
        :rtype: PipelineNode
        """
        self.class_ = nodes.DEFAULT_NODE_MAPPING[node_name]
        self.name = node_name
        self.__parameters = None
        self.__optimization_parameters = None
        self._values = set()
        for parameter, values in task.default_parameters(self).iteritems():
            if not isinstance(values, list):
                values = [values]
            self._values.add(ChoiceParameter(parameter_name=parameter, choices=values))

    @property
    def parameters(self):
        if self.__parameters is None:
            self.__parameters = set()
            for class_ in inspect.getmro(self.class_):
                if class_ != object and hasattr(class_, "__init__"):
                    argspec = inspect.getargspec(class_.__init__)
                    if argspec.defaults is not None:
                        default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
                        self.__parameters.update([arg for arg, default in default_args if arg != "self"])
        return self.__parameters

    @property
    def optimization_parameters(self):
        """
        Returns the names of the parameters of this node.
        If the class that implements this node defines it's hyper parameters, these will be used as
        optimization parameters. Otherwise every parameter of the node's __init__ method that has a default of type
        bool, float, int  is considered as a parameter of the node except for:
            - self
            - .*debug.*
            - .*warn.*

        :return: A list of the parameters of this node.
        :rtype: list[str]
        """
        if self.__optimization_parameters is None:
            if not hasattr(self.class_, PARAMETER_ATTRIBUTE):
                self.__optimization_parameters = set()
                for class_ in inspect.getmro(self.class_):
                    if class_ != object and hasattr(class_, "__init__"):
                        argspec = inspect.getargspec(class_.__init__)
                        if argspec.defaults is not None:
                            default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
                            self.__optimization_parameters.update([arg for arg, default in default_args
                                                                   if arg != "self" and
                                                                   arg.lower().find("debug") == -1 and
                                                                   arg.lower().find("warn") == -1 and
                                                                   arg not in self._values and
                                                                   isinstance(default, (bool, float, int))])
            else:
                self.__optimization_parameters = set([parameter.parameter_name for parameter in
                                                      getattr(self.class_, PARAMETER_ATTRIBUTE)])
            self.__optimization_parameters.update([parameter.parameter_name for parameter in self._values])
        return self.__optimization_parameters

    def parameter_space(self):
        """
        Returns a dictionary of all parameters of this node and their default values.
        If a parameter does not have a default, it is ignored and it is the responsibility of caller to ensure,
        that this parameter get's a value.
        This property should be overwritten in subclasses to create a real space from it, otherwise
        only the default values are used as the space of the parameters.

        :return: A dictionary containing all parameters and their default values.
        :rtype: dict[str, object]
        """
        if not hasattr(self.class_, PARAMETER_ATTRIBUTE):
            # Return 1 for every parameter not set
            space = set()
            parameters = self.optimization_parameters
            for class_ in inspect.getmro(self.class_):
                if class_ != object and hasattr(class_, "__init__"):
                    argspec = inspect.getargspec(class_.__init__)
                    if argspec.defaults is not None:
                        default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
                        for param, default in default_args:
                            if param in parameters:
                                if isinstance(default, bool):
                                    # Add a boolean choice
                                    space.add(BooleanParameter(param))
                                elif isinstance(default, float):
                                    # Add a normal distribution
                                    space.add(NormalParameter(param, mu=default, sigma=1))
                                elif isinstance(default, int):
                                    # Add a Q-Normal distribution
                                    space.add(QNormalParameter(param, mu=default, sigma=1, q=1))
        else:
            space = copy.deepcopy(getattr(self.class_, PARAMETER_ATTRIBUTE))
        # Update with the default values
        values = copy.copy(self._values)
        values.update(space)
        # Create a dictionary containing the optimization name as a key
        return {self._make_parameter_name(parameter.parameter_name): parameter
                for parameter in values}

    def as_dictionary(self):
        """
        Returns the specification as a dictionary usable for pySPACE execution.
        Every parameter of the node is replaced with a variable called __{node_name}_{parameter}__ to ensure
        uniqueness.

        :return: The specification of the node as a dictionary for pySPACE.
        :rtype: dict[str, object]
        """
        result = {"node": self.name}
        if self.optimization_parameters:
            result["parameters"] = {param: "${%s}" % self._make_parameter_name(param)
                                    for param in self.optimization_parameters}
        return result

    def _make_parameter_name(self, parameter):
        """
        Creates an unique name for the given parameter.
        This method uses the scheme __{node_name}_{parameter}__ to make each parameter a unique variable.

        :param parameter: The name of the parameter to make unique
        :type parameter: str
        :return: A unique name for the given parameter.
        :rtype: str
        """
        return "{node_name}_{parameter}".format(
            node_name=self.name,
            parameter=parameter
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.name == self.name
        return False

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


class PipelineSinkNode(PipelineNode):

    def __init__(self, node_name, task):
        super(PipelineSinkNode, self).__init__(node_name, task=task)
        self._main_class = task["main_class"]
        self._class_labels = task["class_labels"]
        self._property = "ir_class"

    @property
    def optimization_parameters(self):
        return []

    def as_dictionary(self):
        return {"node": self.name,
                "parameters": {
                    "ir_class": self._main_class,
                    "classes_names": self._class_labels
                }}


class PipelineSourceNode(PipelineNode):
    @property
    def optimization_parameters(self):
        return []
