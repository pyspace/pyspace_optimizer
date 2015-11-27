import os
import unittest
from pyspace_hyperopt import PySPACEHyperopt
from pyspace_test import PySPACETestCase


class PySPACEHyperoptTestCase(PySPACETestCase):

    def test_optimization(self):
        data_set_dir = os.path.join(self.configuration.examples_storage, "example_summary", "Titanic")
        optimizer = PySPACEHyperopt(data_set_dir,
                                    max_pipeline_length=2,
                                    metric="",
                                    backend="mcore",
                                    max_evaluations=10)
        best_params = optimizer.optimize()
        self.assertIsNotNone(best_params)


if __name__ == '__main__':
    unittest.main()
