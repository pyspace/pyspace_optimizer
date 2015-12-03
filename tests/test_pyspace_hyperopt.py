from configuration import Configuration
from pyspace_test import PySPACETestCase
from optimizer.pyspace_hyperopt import HyperoptOptimizer
from nose.tools import nottest

class HyperoptOptimizerTestCase(PySPACETestCase):

    def test_optimization(self):
        experiment = Configuration("example_summary_split",
                                   optimizer="HyperoptOptimizer",
                                   class_labels=["Standard","Target"],
                                   main_class="Target",
                                   max_pipeline_length=4,
                                   metric="",
                                   max_evaluations=10,
                                   source_node="FeatureVectorSourceNode",
                                   whitelist=["SorSvmNode",
                                              "GaussianFeatureNormalizationNode"])
        optimizer = experiment.optimizer(experiment, backend="mcore")
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)
