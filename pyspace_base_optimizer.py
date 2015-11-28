#!/bin/env python
# -*- coding: utf-8 -*-

import abc
import os
import pySPACE
import glob
from pySPACE.resources.dataset_defs.base import BaseDataset


class PySPACEOptimizer(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, data_set_dir, metric):
        self.data_set_dir = data_set_dir
        self.metric = metric

    @property
    def data_set_type(self):
        # Determinate the type of the data set
        if not os.path.isabs(self.data_set_dir):
            # we need to have an absolut path here, assume it's relative to the storage loation
            data_set_dir = os.path.join(pySPACE.configuration.storage, self.data_set_dir, "*", "")
        else:
            data_set_dir = self.data_set_dir
        old_data_set_type = None
        for file in glob.glob(data_set_dir):
            data_set_type = BaseDataset.load_meta_data(file)["type"]
            if old_data_set_type is not None and data_set_type != old_data_set_type:
                raise TypeError("Inconsistent Data sets found: %s != %s" % (old_data_set_type, data_set_type))
            old_data_set_type = data_set_type
        if old_data_set_type is None:
            raise AttributeError("No data sets found at '%s'" % data_set_dir)
        return old_data_set_type.title().replace("_", "")

    @abc.abstractmethod
    def optimize(self):
        raise NotImplementedError()
