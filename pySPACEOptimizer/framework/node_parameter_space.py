import copy
import inspect

from pySPACE.missions import nodes
from pySPACE.missions.nodes.decorators import PARAMETER_ATTRIBUTE, PARAMETER_TYPES, ChoiceParameter, NormalParameter, \
    QNormalParameter, BooleanParameter, NoOptimizationParameter, ParameterDecorator


class NodeParameterSpace(object):
    def __init__(self, node_name, task):
        """
        Creates a new node for a pipeline using the given pySPACE node name.

        :param node_name: The name of the node to create a pipeline element for.
        :type node_name: str
        :param task: The task to execute with the pipeline this node is used in
        :type task: T <= Task
        :return: A new pipeline element wrapping the given pySPACE node.
        :rtype: NodeParameterSpace
        """
        self.class_ = nodes.DEFAULT_NODE_MAPPING[node_name]
        self.name = node_name
        self.__parameters = None
        self._values = set()
        for parameter, values in task.default_parameters(self).iteritems():
            if isinstance(values, dict):
                type_ = values.get("type", None)
                if type_ is not None:
                    del values["type"]
                    values["parameter_name"] = parameter
                    self._values.add(PARAMETER_TYPES[type_](**values))
            else:
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
                    self.__parameters.update([arg for arg in argspec.args if arg != "self" and
                                              arg.lower().find("debug") == -1 and
                                              arg.lower().find("warn") == -1])
        return self.__parameters

    def parameter_space(self):
        """
        Returns a dictionary of all parameters of this node and their default values.
        If a parameter does not have a default, it is ignored and it is the responsibility of caller to ensure,
        that this parameter get's a value.
        This property should be overwritten in subclasses to create a real space from it, otherwise
        only the default values are used as the space of the parameters.

        :return: A dictionary containing all parameters and their default values.
        :rtype: dict[str, ParameterDecorator]
        """
        space = copy.deepcopy(getattr(self.class_, PARAMETER_ATTRIBUTE, set()))
        # If no optimization parameters have been defined
        # try to get them from the __init__ method
        if not space or all([isinstance(parameter, NoOptimizationParameter) for parameter in space]):
            for class_ in inspect.getmro(self.class_):
                if class_ != object and hasattr(class_, "__init__"):
                    argspec = inspect.getargspec(class_.__init__)
                    if argspec.defaults is not None:
                        default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
                        for param, default in default_args:
                            if all([value not in param.lower() for value in ["self", "debug", "warn"]]) and \
                                            param not in space:
                                if isinstance(default, bool):
                                    # Add a boolean choice
                                    space.add(BooleanParameter(param))
                                elif isinstance(default, float):
                                    # Add a normal distribution
                                    space.add(NormalParameter(param, mu=default, sigma=1))
                                elif isinstance(default, int):
                                    # Add a Q-Normal distribution
                                    space.add(QNormalParameter(param, mu=default, sigma=1, q=1))
                                elif isinstance(default, (list, tuple)):
                                    space.add(ChoiceParameter(param, choices=default))

        # Update with the default values
        values = copy.copy(self._values)
        values.update(space)
        # Create a dictionary containing the optimization name as a key
        return {self._make_parameter_name(parameter): parameter for parameter in values
                if not isinstance(parameter, NoOptimizationParameter)}

    def as_dictionary(self):
        """
        Returns the specification as a dictionary usable for pySPACE execution.
        Every parameter of the node is replaced with a variable called __{node_name}_{parameter}__ to ensure
        uniqueness.

        :return: The specification of the node as a dictionary for pySPACE.
        :rtype: dict[str, str|bool|float|int|dict[str, str|bool|float|int]]
        """
        result = {"node": self.name}
        space = self.parameter_space()
        if space:
            result["parameters"] = {}
            for parameter in self.parameters:
                parameter_name = self._make_parameter_name(parameter)
                if parameter_name in space:
                    # noinspection PyUnresolvedReferences
                    result["parameters"][parameter] = "${{{name}}}".format(name=parameter_name)
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

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return hash(self.name)


class SinkNodeParameterSpace(NodeParameterSpace):

    def __init__(self, node_name, task):
        super(SinkNodeParameterSpace, self).__init__(node_name, task=task)
        self._main_class = task["main_class"]
        self._class_labels = task["class_labels"]
        self._property = "ir_class"

    def parameter_space(self):
        return {self._make_parameter_name(parameter): parameter for parameter in self._values}

    def as_dictionary(self):
        result = super(SinkNodeParameterSpace, self).as_dictionary()
        if "parameters" not in result:
            result["parameters"] = {}
        result["parameters"]["ir_class"] = self._main_class
        result["parameters"]["classes_names"] = self._class_labels
        return result


class SourceNodeParameterSpace(NodeParameterSpace):

    def parameter_space(self):
        return {self._make_parameter_name(parameter): parameter for parameter in self._values}
