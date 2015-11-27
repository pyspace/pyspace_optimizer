#!/bin/env python
# -*- coding: utf-8 -*-

import abc
from resources.dataset_defs.base import BaseDataset


class PySPACEOptimizer(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, data_set_dir, metric):
        self.data_set_dir = data_set_dir
        self.metric = metric

    @property
    def data_set_type(self):
        # Determinate the type of the data set
        dataset_type = BaseDataset.load_meta_data(self.data_set_dir)["type"]
        return dataset_type.title().replace("_", "")

    @abc.abstractmethod
    def optimize(self):
        raise NotImplementedError()
