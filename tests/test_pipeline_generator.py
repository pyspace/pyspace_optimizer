from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.tasks.base_task import Task
from pyspace_test import PySPACETestCase


class PipelineGeneratorTests(PySPACETestCase):

    def test_generate_pipelines(self):
        experiment = Task(input_path="example_summary_split",
                          optimizer="PySPACEOptimizer",
                          class_labels=["Standard", "Target"],
                          main_class="Target",
                          max_pipeline_length=3,
                          evaluations_per_pass=1)
        generator = PipelineGenerator(experiment)
        for pipeline in generator:
            self.assertLessEqual(len(pipeline), experiment["max_pipeline_length"])

    def test_whitelist(self):
        task = Task(input_path="example_summary_split",
                    optimizer="PySPACEOptimizer",
                    class_labels=["Standard", "Target"],
                    main_class="Target",
                    source_node="FeatureVectorSourceNode",
                    sink_node="PerformanceSinkNode",
                    whitelist=["SorSvmNode", "GaussianFeatureNormalizationNode"],
                    evaluations_per_pass=1)
        check = task["whitelist"]
        check.add(task["source_node"])
        check.add(task["sink_node"])
        for pipeline in PipelineGenerator(task):
            self.assertTrue(set(pipeline).issubset(check))

    def test_blacklist(self):
        task = Task(input_path="example_summary_split",
                    optimizer="PySPACEOptimizer",
                    class_labels=["Standard", "Target"],
                    main_class="Target",
                    source_node="FeatureVectorSourceNode",
                    sink_node="PerformanceSinkNode",
                    blacklist=["SorSvmNode", "GaussianFeatureNormalizationNode"],
                    evaluations_per_pass=1)
        for pipeline in PipelineGenerator(task):
            self.assertFalse(any([node in pipeline for node in task["blacklist"]]))

    def test_forced_nodes(self):
        task = Task(input_path="example_summary_split",
                    optimizer="PySPACEOptimizer",
                    class_labels=["Standard", "Target"],
                    main_class="Target",
                    forced_nodes=["SorSvmNode"],
                    evaluations_per_pass=1)
        for pipeline in PipelineGenerator(task):
            self.assertTrue(all([node in pipeline for node in task["forced_nodes"]]))
