from configuration import Configuration
from pyspace_test import PySPACETestCase
from nose.tools import nottest

class HyperoptOptimizerTestCase(PySPACETestCase):

    @nottest
    def test_optimization(self):
        experiment = Configuration("example_summary",
                                   optimizer="HyperoptOptimizer",
                                   max_processing_length=2,
                                   metric="",
                                   max_evaluations=10,
                                   source_node="FeatureVectorSourceNode",
                                   splitter_node="TrainTestSplitterNode",
                                   whitelist=["FeatureVectorSourceNode",
                                           "TrainTestSplitterNode",
                                           "SorSvmNode",
                                           "PerformanceSinkNode",
                                           "GaussianFeatureNormalizationNode"])
        optimizer = experiment.optimizer(experiment, backend="mcore")
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)
