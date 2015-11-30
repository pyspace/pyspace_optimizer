import unittest

from configuration import Configuration
from optimizer.pyspace_base_optimizer import PySPACEOptimizer
from pipelines import PipelineNode
from pyspace_test import PySPACETestCase


class ExperimentTestCase(PySPACETestCase):

    def test_weighted_nodes_by_input_type(self):
        node = PipelineNode("FeatureVectorSourceNode")
        experiment = Configuration("example_summary", optimizer=PySPACEOptimizer, node_weights={
            node.name: 10,
        })
        nodes = experiment.weighted_nodes_by_input_type()
        for input_type in node.class_.get_input_types():
            self.assertEqual(node.name, nodes[input_type][0])

    def test_white_list(self):
        white_list = ["FeatureVectorSourceNode", "TrainTestSplitterNode", "PerformanceSinkNode"]
        experiment = Configuration("example_summary", optimizer=PySPACEOptimizer, whitelist=white_list)
        self.assertEqual(len(experiment.nodes), len(white_list))

    @unittest.expectedFailure
    def test_wrong_weight_dict(self):
        weight_list = {"NotExistingNode": 1337}
        Configuration("example_summary", optimizer=PySPACEOptimizer, node_weights=weight_list)

    @unittest.expectedFailure
    def test_wrong_weight_dict2(self):
        weight_list = {"FeatureVectorSourceNode": -42}
        Configuration("example_summary", optimizer=PySPACEOptimizer, node_weights=weight_list)

    @unittest.expectedFailure
    def test_wrong_white_list(self):
        white_list = ["NotExistingNode"]
        Configuration("example_summary", optimizer=PySPACEOptimizer, whitelist=white_list)
