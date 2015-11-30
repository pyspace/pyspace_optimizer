import yaml
from pipelines import Pipeline
from pyspace_test import PySPACETestCase


class PipelineTestCase(PySPACETestCase):

    def test_operation_spec(self):
        pipeline = Pipeline.from_node_list(["SorSvmNode", "PerformanceSinkNode"], "")
        operation_spec = pipeline.operation_spec
        self.assertIsNotNone(operation_spec)
        parsed = yaml.load(operation_spec["base_file"])
        self.assertDictContainsSubset(parsed, operation_spec)
