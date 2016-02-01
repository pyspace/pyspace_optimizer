#!/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from argparse import ArgumentParser

import pySPACE
from pySPACEOptimizer.optimizer import optimizer_factory, list_optimizers
from pySPACEOptimizer.tasks import task_from_yaml, list_tasks

try:
    import cPickle as pickle
except ImportError:
    import pickle


def create_parser():
    home = os.path.expanduser("~")
    # TODO: Description and usage
    parser = ArgumentParser(description="Launch the optimization of the given task using the given backend",
                            usage="%(prog)s -c CONFIG [-h | --list-optimizer | --list-tasks]\n\t%(prog)s -t TASK [-b BACKEND]")
    parser.add_argument("-c", "--config", type=str, help="The name of the pySPACEcenter configuration to load",
                        default="config.yaml")
    parser.add_argument("-t", "--task", type=str, help="The path to a task description in YAML format")
    parser.add_argument("-b", "--backend", type=str, default="serial",
                        help='The backend to use for testing in pySPACE. '
                             'Possible values: "serial", "mcore", "mpi", "loadl". Default: "serial"')
    parser.add_argument("--list-optimizer", action="store_true", default=False,
                        help="List all available optimizers and quit")
    parser.add_argument("--list-tasks", action="store_true", default=False,
                        help="List all available optimization tasks and quit")
    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = create_parser()
    arguments = parser.parse_args(args)

    # Load the configuration
    pySPACE.load_configuration(arguments.config)

    if arguments.list_optimizer:
        print("Listing all available optimizers:")
        for optimizer in list_optimizers():
            print("\t- %s" % optimizer)
    elif arguments.list_tasks:
        print("Listing all available tasks:")
        for task in list_tasks():
            print("\t- %s" % task)
    else:
        print("Start optimization..")
        with open(arguments.task, "rb") as file_:
            task = task_from_yaml(file_)
        optimizer = optimizer_factory(task, arguments.backend)
        best_result = optimizer.optimize()
        print("Done..")
        file_ = os.path.join(os.getcwd(), "best_result.pickle")
        print("Best result will be stored as: %s" % file_)
	with open(file_, "wb") as best_file:
            pickle.dump(best_result, best_file)


if __name__ == "__main__":
    main()
