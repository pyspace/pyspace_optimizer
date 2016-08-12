from pySPACEOptimizer.optimizer import optimizer_factory
from pySPACEOptimizer.tasks import task_factory
from pyspace_test import PySPACETestCase


class HyperoptOptimizerTestCase(PySPACETestCase):

    def test_optimization(self):
        task_spec = dict(type="classification",
                         input_path="example_summary_split",
                         optimizer="HyperoptOptimizer",
                         class_labels=["Standard", "Target"],
                         main_class="Target",
                         max_pipeline_length=4,
                         evaluations_per_pass=1,
                         source_node="FeatureVectorSourceNode",
                         whitelist=["SorSvmNode"],
                         parameter_ranges={"SorSvmNode": {
                                                "complexity": 1,
                                                "max_iterations": 10
                                           }})
        task = task_factory(task_spec)
        optimizer = optimizer_factory(task, backend="mcore")
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)
