import os

from pySPACEOptimizer.optimizer import optimizer_factory
from pySPACEOptimizer.tasks import task_factory
from pyspace_test import PySPACETestCase

try:
    import cPickle as pickle
except ImportError:
    import pickle


class HyperoptOptimizerTestCase(PySPACETestCase):

    def test_optimization(self):
        task_spec = dict(type="classification",
                         input_path="example_summary_split",
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
                                    "complexity": 1,
                                    # "kernel_type": "LINEAR",
                                    "max_iterations": 10
                            }}
                         ])
        task = task_factory(task_spec)
        optimizer = optimizer_factory(task, backend="mcore", best_result_file="test.yaml")
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)
