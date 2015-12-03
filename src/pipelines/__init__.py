#!/bin/env python
# -*- coding: utf-8 -*-
#!/bin/env python
# -*- coding: utf-8 -*-
import inspect
import yaml

import pySPACE
from pySPACE.missions import nodes
try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper


class PipelineNode(object):

    def __init__(self, node_name):
        """
        Creates a new node for a pipeline using the given pySPACE node name.

        :param node_name: The name of the node to create a pipeline element for.
        :type node_name: str
        :return: A new pipeline element wrapping the given pySPACE node.
        :rtype: PipelineNode
        """
        self.class_ = nodes.DEFAULT_NODE_MAPPING[node_name]
        self.name = node_name
        self._values = {}

    @property
    def parameters(self):
        """
        Returns the names of the parameters of this node.
        Every parameter to the node's __init__ method is considered as a parameter of the node.

        :return: A list of the parameters of this node.
        :rtype: list[str]
        """
        argspec = inspect.getargspec(self.class_.__init__)
        return [arg for arg in argspec.args if arg != "self"]

    @property
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
        space = {}
        parameters = self.parameters
        argspec = inspect.getargspec(self.class_.__init__)
        if argspec.defaults is not None:
            default_args = zip(argspec.args[-len(argspec.defaults):], argspec.defaults)
            space = {self._make_parameter_name(param): default for param, default in default_args
                     if param in parameters}
        return space

    def as_dictionary(self):
        """
        Returns the specification as a dictionary usable for pySPACE execution.
        Every parameter of the node is replaced with a variable called __{node_name}_{parameter}__ to ensure
        uniqueness.

        :return: The specification of the node as a dictionary for pySPACE.
        :rtype: dict[str, object]
        """
        result = {"node": self.name}
        if self.parameters:
            result["parameters"] = {param: self._make_parameter_name(param) for param in self.parameters}
        if self._values:
            if "parameters" not in result:
                result["parameters"] = self._values
            else:
                result["parameters"].update(self._values)
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
        return "__{node_name}_{parameter}__".format(
            node_name=self.name,
            parameter=parameter
        )

    def set_value(self, parameter, value):
        if parameter in self.parameters:
            self._values[parameter] = value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.name == self.name
        return False

    def __repr__(self):
        return self.name


class SinkNode(PipelineNode):

    def __init__(self, node_name, main_class, class_property="ir_class"):
        super(SinkNode, self).__init__(node_name)
        self._main_class = main_class
        self._property = class_property
        self.set_value(self._property, self._main_class)

    @property
    def parameters(self):
        return []


class Pipeline(list):

    def __init__(self, configuration, node_chain=None):
        """
        Creates a new node with the given `name` and `data_set_path`.
        The pipeline uses the given nodes for processing.

        :param configuration: The configuration to use for this Pipeline
        :type configuration: Configuration
        :param node_chain: A list of node names to create the pipeline with
        :type node_chain: [PipelineNode]

        :return: A new PySPACEPipeline with the given name, nodes and data set path
        :rtype: Pipeline
        """
        super(Pipeline, self).__init__(node_chain if node_chain is not None else [])
        self._input_path = configuration.data_set_path
        self._parameter_ranges = {}
        self._node_class = PipelineNode

    @property
    def pipeline_space(self):
        """
        Returns the parameter space of the pipeline.
        The parameter space is a dictionary of the parameters used in this pipeline and their ranges.
        This method automatically excludes the first and the last node, as these are normally a source and a sink
        node that should not be optimized at all.

        :return: The domain of the parameters for this pipeline
        :rtype: dict[str, str]
        """
        space = {}
        for node in self[1:-1]:
            space.update(node.parameter_space)
        return space

    @property
    def pipeline_parameters(self):
        """
        Returns the names of the parameters used in the pipeline.
        These are the named of the parameters of every node inside the pipeline.

        :return: The parameter names of the pipeline
        :rtype: list[str]
        """
        parameters = []
        for node in self:
            for parameter in node.parameter_space.iterkeys():
                parameters.append(parameter)
        return parameters

    def set_parameter(self, parameter_name, values):
        """
        Sets the parameter with the given `parameter_name` to the given list of values.
        This method raises an AttributeError either if the `parameter_name` is not found in the domain of the pipeline
        of if the `values` aren't a list.

        :param parameter_name: The name of the parameter to set.
        :type parameter_name: str
        :param values: A list of possible values to set for the parameter.
        :raises: AttributeError
        """
        if parameter_name not in self.pipeline_parameters:
            raise AttributeError("Parameter '%s' not found in the pipeline" % parameter_name)
        if not isinstance(values, list):
            raise AttributeError("Only lists of values are supported as parameter ranges")
        self._parameter_ranges[parameter_name] = values

    @property
    def operation_spec(self):
        """
        Return the pipeline as an operation specification usable for pySPACE execution.

        :return: The pipeline specification as a dictionary
        :rtype: dict[str, str]
        """
        node_chain = [node.as_dictionary() for node in self]
        operation_spec = {
            "type": "node_chain",
            "input_path": self._input_path,
            "node_chain": node_chain,
            "parameter_ranges": self._parameter_ranges
        }
        # Due to bad pySPACE YAML-Parsing, we need to modify the output of the yaml dumper for correct format
        dump = yaml.dump(operation_spec, Dumper=Dumper, default_flow_style=False, indent=4)
        lines = []
        for line in dump.split("\n"):
            if line.startswith(" ") or line.startswith("-"):
                lines.append("    " + line)
            else:
                lines.append(line)
        operation_spec["base_file"] = "\n".join(lines)
        return operation_spec

    def execute(self, backend=u"serial"):
        """
        Executes the pipeline using the given backend.

        :param backend: The backend to use for execution. (Default: serial)
        :type backend: unicode
        :return: The path to the results of the pipeline
        :rtype: unicode
        """
        backend = pySPACE.create_backend(backend)
        operation = pySPACE.create_operation(self.operation_spec)
        return pySPACE.run_operation(backend, operation)

    def append(self, node_name):
        if isinstance(node_name, str):
            node_name = self._node_class(node_name)
        elif not isinstance(node_name, PipelineNode):
            raise TypeError("Node '%s' is not of type %s" % (node_name, PipelineNode))
        return super(Pipeline, self).append(node_name)

    def remove(self, node_name):
        if isinstance(node_name, str):
            node_name = self._node_class(node_name)
        if isinstance(node_name, PipelineNode):
            return super(Pipeline, self).remove(node_name)

    def __setitem__(self, index, node_name):
        if isinstance(node_name, str):
            node_name = self._node_class(node_name)
        elif not isinstance(node_name, PipelineNode):
            raise TypeError("Node '%s' is not of type %s" % (node_name, PipelineNode))
        super(Pipeline, self).__setitem__(index, node_name)

    def __contains__(self, node_name):
        if isinstance(node_name, str):
            node_name = self._node_class(node_name)
        return super(Pipeline, self).__contains__(node_name)
