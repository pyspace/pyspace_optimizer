import unittest
from pySPACE.missions.nodes import DEFAULT_NODE_MAPPING
from pySPACE.missions.nodes.decorators import PARAMETER_ATTRIBUTE, NoOptimizationParameter, ChoiceParameter
from pySPACEOptimizer.framework.base_task import Task
from pySPACEOptimizer.framework.node_parameter_space import NodeParameterSpace


class NodeParameterSpaceTestCase(unittest.TestCase):
    def setUp(self):
        super(NodeParameterSpaceTestCase, self).setUp()
        self.task = Task(name="NodeParameterSpaceTest", input_path="example_summary_split", evaluations_per_pass=10)

    def testNoOptimizationParameters(self):
        node_name = "GaussianFeatureNormalizationNode"
        node = NodeParameterSpace(node_name=node_name, task=self.task)
        parameters = getattr(DEFAULT_NODE_MAPPING[node_name], PARAMETER_ATTRIBUTE, set())
        if parameters:
            parameter_space = node.parameter_space()
            self.assertTrue(all([not isinstance(parameters[name], NoOptimizationParameter)
                                 for name in parameter_space.values()]))
        else:
            self.fail("The Node '%s' does not have any decorators" % node_name)

    def testOverwriteDefaultWithParameter(self):
        node_name = "GaussianFeatureNormalizationNode"
        parameter_name = "store"
        self.task["parameter_ranges"].append({"node": node_name, "parameters": {parameter_name: {"type": "Boolean"}}})
        node = NodeParameterSpace(node_name=node_name, task=self.task)
        self.assertTrue(parameter_name in node.parameter_space().values())

    def testOverwriteDefaultWithSingleValue(self):
        node_name = "GaussianFeatureNormalizationNode"
        parameter_name = "store"
        value = True
        self.task["parameter_ranges"].append({"node": node_name, "parameters": {parameter_name: value}})
        node = NodeParameterSpace(node_name=node_name, task=self.task)
        space = node.parameter_space().values()
        self.assertTrue(parameter_name in space)
        parameter = [parameter for parameter in space if parameter.parameter_name == parameter_name][0]
        self.assertIsInstance(parameter, ChoiceParameter)
        self.assertIn(value, parameter.choices)

    def testOverwriteDefaultWithMultipleValues(self):
        node_name = "GaussianFeatureNormalizationNode"
        parameter_name = "store"
        values = [True, False]
        self.task["parameter_ranges"].append({"node": node_name, "parameters": {parameter_name: values}})
        node = NodeParameterSpace(node_name=node_name, task=self.task)
        space = node.parameter_space().values()
        self.assertTrue(parameter_name in space)
        parameter = [parameter for parameter in space if parameter.parameter_name == parameter_name][0]
        self.assertIsInstance(parameter, ChoiceParameter)
        self.assertListEqual(values, parameter.choices)


if __name__ == '__main__':
    unittest.main()
