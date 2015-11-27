import unittest
from pipeline_generator import PipelineGenerator
from pyspace_test import PySPACETestCase

class PipelineGeneratorTests(PySPACETestCase):

    def test_generate_pipelines(self):
        max_length = 3
        generator = PipelineGenerator("FeatureVector", max_length)
        for pipeline in generator:
            self.assertLessEqual(len(pipeline), max_length)


if __name__ == '__main__':
    unittest.main()
