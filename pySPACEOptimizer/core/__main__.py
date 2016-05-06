#!/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import logging
import logging.config
import yaml
from argparse import ArgumentParser, FileType

import pySPACE
from pySPACEOptimizer.framework import optimizer_factory, list_optimizers, task_from_yaml, list_tasks


HOME = os.path.expanduser("~")


def create_parser():
    parser = ArgumentParser(description="Launch the optimization of the given task using the given backend",
                            usage="%(prog)s -c CONFIG [-h | --list-optimizer | --list-tasks]\n"
                                  "\t%(prog)s -c CONFIG -t TASK [-b BACKEND] [-r RESULT]")
    parser.add_argument("-c", "--config", type=str, help="The name of the pySPACEcenter configuration to load",
                        default="config.yaml")
    parser.add_argument("-t", "--task", type=FileType("rb"),
                        help="The path to a task description in YAML format", required=True)
    parser.add_argument("-r", "--result", type=str, default=None,
                        help="The path to store the results (logging, performance, trials, ...) to")
    parser.add_argument("-b", "--backend", type=str, default="serial",
                        help='The backend to use for testing in pySPACE. '
                             'Possible values: "serial", "mcore", "mpi", "loadl". Default: "serial"')
    parser.add_argument("--list-optimizer", action="store_true", default=False,
                        help="List all available optimizers and quit")
    parser.add_argument("--list-tasks", action="store_true", default=False,
                        help="List all available optimization tasks and quit")
    return parser


def init_logging(config_file="pySPACEOptimizer.yaml"):
    # read the config file
    if os.path.isfile(config_file):
        with open(config_file, "rb") as file_:
            config = yaml.load(file_)
        # init the logging
        logging.config.dictConfig(config)
        # Capture warnings
        logging.captureWarnings(True)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = create_parser()
    arguments = parser.parse_args(args)

    # Load the configuration
    old_stdout = sys.stdout
    try:
        sys.stdout = open(os.devnull, "wb")
        pySPACE.load_configuration(arguments.config)
    finally:
        sys.stdout = old_stdout

    if arguments.list_optimizer:
        print("Listing all available optimizers:")
        for optimizer in list_optimizers():
            print("\t- %s" % optimizer)
    elif arguments.list_tasks:
        print("Listing all available tasks:")
        for task in list_tasks():
            print("\t- %s" % task)
    else:
        # Init the logging
        init_logging()
        # Get the logger
        logger = logging.getLogger("pySPACEOptimizer")
        # noinspection PyBroadException
        try:
            logger.info("Start optimization..")
            task = task_from_yaml(arguments.task)
            if arguments.result is not None:
                task.base_result_dir = arguments.result

            result = os.path.join(task.base_result_dir, "best.yaml")
            logger.info("Best result will be stored as: %s" % result)

            optimizer = optimizer_factory(task, arguments.backend, result)
            if optimizer is None:
                raise Exception("Optimizer %s not found!" % task["optimizer"])
            best_result = optimizer.do_optimization()
            logger.info("Done!")
            logger.info("Best result found: %s", best_result)
        except Exception:
            logger.exception("Error!")
        finally:
            logging.shutdown()


if __name__ == "__main__":
    main()
