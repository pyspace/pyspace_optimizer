from pySPACEOptimizer.optimizer import optimizer_factory
from pySPACEOptimizer.tasks.classification import ClassificationTask
from pyspace_test import PySPACETestCase


class HyperoptOptimizerTestCase(PySPACETestCase):

    def test_optimization(self):
        experiment = ClassificationTask(input_path="example_summary_split",
                                        optimizer="HyperoptOptimizer",
                                        class_labels=["Standard", "Target"],
                                        main_class="Target",
                                        max_pipeline_length=4,
                                        max_evaluations=1,
                                        max_eval_time=0,  # seconds
                                        source_node="FeatureVectorSourceNode",
                                        whitelist=[
                                                     "SorSvmNode",
                                                     "GaussianFeatureNormalizationNode"],
                                        parameter_ranges=[
                                                     {"node": "SorSvmNode",
                                                      "parameters": {
                                                          # "kernel_type": "LINEAR",
                                                          "max_iterations": 10
                                                      }}
                                        ])
        optimizer = optimizer_factory(experiment, backend="mcore")
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)
