import unittest
import pySPACE


class PySPACETestCase(unittest.TestCase):

    def setUp(self):
        self.configuration = pySPACE.load_configuration("config.yaml")
