from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.tasks.base_task import Task
from pyspace_test import PySPACETestCase


class PipelineGeneratorTests(PySPACETestCase):

    def test_generate_pipelines(self):
        experiment = Task(input_path="example_summary_split",
                          optimizer="PySPACEOptimizer",
                          class_labels=["Standard","Target"],
                          main_class="Target",
                          max_pipeline_length=3)
        generator = PipelineGenerator(experiment)
        for pipeline in generator:
            self.assertLessEqual(len(pipeline), experiment["max_pipeline_length"])
