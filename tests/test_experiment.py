import unittest

from pySPACEOptimizer.configuration import Configuration, is_source_node, is_sink_node
from pySPACEOptimizer.optimizer.pyspace_base_optimizer import PySPACEOptimizer
from pySPACEOptimizer.pipelines import PipelineNode
from pyspace_test import PySPACETestCase


MINIMAL_CONFIG="""
input_path: "example_summary_split"
optimizer: HyperoptOptimizer
class_labels: [Standard, Target]
main_class: Target
"""


EXTENDED_CONFIG="""
input_path: "example_summary_split"
optimizer: HyperoptOptimizer
class_labels: [Standard, Target]
main_class: Target

max_pipeline_length: 4
source_node: FeatureVectorSourceNode
whitelist: [SorSvmNode,
            GaussianFeatureNormalizationNode]
max_evaluations: 10

parameter_ranges:
    - node: SorSvmNode
      parameters:
        kernel_type: ["LINEAR"]
        max_iterations: [10]
"""


class ExperimentTestCase(PySPACETestCase):

    def test_weighted_nodes_by_input_type(self):
        node_name = "SorSvmNode"
        experiment = Configuration("example_summary",
                                   optimizer=PySPACEOptimizer,
                                   node_weights={
                                        node_name: 10,
                                   },
                                   class_labels=["Standard","Target"],
                                   main_class="Target")
        node = PipelineNode(node_name, experiment)
        nodes = experiment.weighted_nodes_by_input_type()
        for input_type in node.class_.get_input_types():
            self.assertEqual(node.name, nodes[input_type][0])

    def test_white_list(self):
        white_list = ["SorSvmNode"]
        experiment = Configuration("example_summary",
                                   optimizer=PySPACEOptimizer,
                                   class_labels=["Standard","Target"],
                                   main_class="Target",
                                   whitelist=white_list)
        self.assertEqual(len([node for node in experiment.nodes
                              if not is_source_node(node) and not is_sink_node(node)]),
                         len(white_list))

    @unittest.expectedFailure
    def test_wrong_weight_dict(self):
        weight_list = {"NotExistingNode": 1337}
        Configuration("example_summary",
                      optimizer=PySPACEOptimizer,
                      class_labels=["Standard","Target"],
                      main_class="Target",
                      node_weights=weight_list)

    @unittest.expectedFailure
    def test_wrong_weight_dict2(self):
        weight_list = {"SorSvmNode": -42}
        Configuration("example_summary",
                      optimizer=PySPACEOptimizer,
                      class_labels=["Standard","Target"],
                      main_class="Target",
                      node_weights=weight_list)

    @unittest.expectedFailure
    def test_wrong_white_list(self):
        white_list = ["NotExistingNode"]
        Configuration("example_summary",
                      optimizer=PySPACEOptimizer,
                      class_labels=["Standard","Target"],
                      main_class="Target",
                      whitelist=white_list)

    def test_minimal_config_from_yaml(self):
        config = Configuration.from_yaml(MINIMAL_CONFIG)
        self.assertIsNotNone(config)

    def test_extended_config_from_yaml(self):
        config = Configuration.from_yaml(EXTENDED_CONFIG)
        self.assertIsNotNone(config)
