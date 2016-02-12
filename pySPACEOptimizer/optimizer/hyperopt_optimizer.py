#!/bin/env python
# -*- coding: utf-8 -*-
import numpy
import os
import time
import warnings
import logging
import pySPACE

from hyperopt import fmin, STATUS_OK, tpe, STATUS_FAIL
from hyperopt.mongoexp import MongoTrials, MongoJobs, MongoWorker

from base_optimizer import PySPACEOptimizer
from optimizer_pool import OptimizerPool
from multiprocessing import Process

from pySPACE.missions.nodes.decorators import ChoiceParameter
from pySPACE.resources.dataset_defs.performance_result import PerformanceResultSummary
from pySPACEOptimizer.pipeline_generator import PipelineGenerator
from pySPACEOptimizer.pipelines import Pipeline, PipelineNode
from pySPACEOptimizer.pipelines.nodes.hyperopt_node import HyperoptNode, HyperoptSinkNode, HyperoptSourceNode
from pySPACEOptimizer.tasks.base_task import is_sink_node, is_source_node


MONGODB_CONNECTION = "mongo://%(host)s:%(port)s" % {"host": os.getenv("MONGO_PORT_27017_TCP_ADDR", "localhost"),
                                                    "port": os.getenv("MONGO_PORT_27017_TCP_PORT", "27017")}


def __minimize(spec):
    task, pipeline, backend = spec[0]
    logger = logging.getLogger(__name__)
    parameter_ranges = {param: [value] for param, value in spec[1].iteritems()}
    try:
        with warnings.catch_warnings():
            # Ignore all warnings shown by the pipeline as most of them occur because of the parameters selected
            warnings.simplefilter("ignore")
            result_path = pipeline.execute(parameter_ranges=parameter_ranges, backend=backend)
        summary = PerformanceResultSummary.from_csv(os.path.join(result_path, "results.csv"))
        # Calculate the mean of all data sets using the given metric
        mean = numpy.mean(numpy.asarray(summary[task["metric"]], dtype=numpy.float))
        return {
            "loss": -1 * mean if "is_performance_metric" in task and
                                 task["is_performance_metric"] else mean,
            "status": STATUS_OK
        }
    except Exception:
        logger.exception("Error in Pipeline '%s':", pipeline)
        return {
            "loss": float("inf"),
            "status": STATUS_FAIL
        }


class WorkerProcess(Process):

    def __init__(self, mongodb_connection, exp_key=None, workdir=None):
        super(WorkerProcess, self).__init__(name="HyperoptMongoWorker")
        self.__connection = mongodb_connection
        self.__key = exp_key
        self.__workdir = workdir

    def run(self):
        mj = MongoJobs.new_from_connection_str(self.__connection + '/jobs')
        mworker = MongoWorker(mj, exp_key=self.__key, workdir=self.__workdir)
        while True:
            mworker.run_one()


def optimize_pipeline(args):
    task, pipeline, _ = args
    pipeline_space = [args, pipeline.pipeline_space]
    connection = task["mongodb_connection"] if "mongodb_connection" in task else MONGODB_CONNECTION
    # Store each pipeline in it's own db
    connection += "/%s" % hash(pipeline)
    worker = WorkerProcess(connection, workdir=pySPACE.configuration.storage)
    try:
        # Start the worker
        worker.start()
        # Run the minimizer
        trials = MongoTrials(connection + "/jobs")
        best = fmin(fn=__minimize,
                    space=pipeline_space,
                    algo=task["suggestion_algorithm"] if "suggestion_algorithm" in task else tpe.suggest,
                    max_evals=task["max_evaluations"] if "max_evaluations" in task else 100,
                    trials=trials)
        # Replace indexes of choice parameters with the selected values
        new_pipeline_space = {}
        for node in pipeline.nodes:
            new_pipeline_space.update(super(type(node), node).parameter_space)
        for key, value in best.iteritems():
            if isinstance(new_pipeline_space[key], ChoiceParameter):
                best[key] = new_pipeline_space[key].choices[value]
        return trials.best_trial["result"]["loss"], pipeline, best
    finally:
        worker.terminate()
        worker.join()


class HyperoptOptimizer(PySPACEOptimizer):

    def __init__(self, task, backend="serial"):
        super(HyperoptOptimizer, self).__init__(task, backend)
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
    
    def _generate_pipelines(self):
        for pipeline in PipelineGenerator(self._task):
            self._logger.debug("Generated Pipeline: %s", pipeline)
            pipeline = Pipeline(configuration=self._task,
                                node_chain=[self._create_node(node_name) for node_name in pipeline])
            yield (self._task, pipeline, self._backend)
            # We need to wait at least one second before yielding the next pipeline
            # otherwise the result will be stored within the same result dir
            time.sleep(1)

    def optimize(self):
        self._logger.info("Optimizing Pipelines")
        self._logger.debug("Creating optimization pool")
        pool = OptimizerPool()
        results = pool.imap(optimize_pipeline, self._generate_pipelines())
        pool.close()

        # loss, pipeline, parameters
        best = [float("inf"), None, None]
        for loss, pipeline, parameters in results:
            self._logger.debug("Checking result of pipeline '%s':\nLoss: %s, Parameters: %s", pipeline, loss, parameters)
        if loss < best[0]:
            self._logger.debug("Pipeline '%s' with parameters '%s' selected as best", pipeline, parameters)
            best = [loss, pipeline, parameters]

        pool.join()
        # Return the best result
        self._logger.info("Best result found: %s", best)
        return best

    def _create_node(self, node_name):
        if is_sink_node(node_name):
            return HyperoptSinkNode(node_name=node_name, task=self._task)
        elif is_source_node(node_name):
            return HyperoptSourceNode(node_name=node_name, task=self._task)
        else:
            return HyperoptNode(node_name=node_name, task=self._task)


class SerialHyperoptOptimizer(HyperoptOptimizer):
   def optimize(self):
        self._logger.info("Optimizing Pipelines")
        self._logger.debug("Creating optimization pool")
        best = [None, float("inf")]
        
        for args in self._generate_pipelines():
            loss, pipeline, parameters = optimize_pipeline(args)
            self._logger.debug("Loss of Pipeline '%s' is: '%s'", pipeline, loss)
            if loss < best[0]:
                self._logger.debug("Pipeline '%s' with parameters '%s' selected as best", pipeline, parameters)
                best = [params, loss]

        self._logger.info("Best result found: %s", best)
        return best
