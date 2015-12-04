import yaml

from pySPACEOptimizer.configuration import Configuration
from pySPACEOptimizer.pipelines import Pipeline
from pyspace_test import PySPACETestCase


class PipelineTestCase(PySPACETestCase):

    def test_operation_spec(self):
        experiment = Configuration(input_path="example_summary_split",
                                   optimizer="PySPACEOptimizer",
                                   class_labels=["Standard","Target"],
                                   main_class="Target")
        pipeline = Pipeline(experiment)
        pipeline.extend(["SorSvmNode", "PerformanceSinkNode"])
        operation_spec = pipeline.operation_spec()
        self.assertIsNotNone(operation_spec)
        parsed = yaml.load(operation_spec["base_file"])
        self.assertDictContainsSubset(parsed, operation_spec)
