from configuration import Configuration
from optimizer.pyspace_base_optimizer import PySPACEOptimizer
from pipeline_generator import PipelineGenerator
from pyspace_test import PySPACETestCase


class PipelineGeneratorTests(PySPACETestCase):

    def test_generate_pipelines(self):
        experiment = Configuration(data_set_path="example_summary",
                                   max_processing_length=1,
                                   optimizer=PySPACEOptimizer)
        generator = PipelineGenerator(experiment)
        for pipeline in generator:
            self.assertLessEqual(len(pipeline), experiment.max_processing_length + 3)
