#!/bin/env python
# -*- coding: utf-8 -*-
import sys
from argparse import ArgumentParser

from pySPACEOptimizer.optimizer import optimizer_factory
from pySPACEOptimizer.tasks.base_task import Task


def create_parser():
    # TODO: Description and usage
    parser = ArgumentParser()
    parser.add_argument("-e", "--experiment", type=str, help="The path to an experiment description in YAML format")
    parser.add_argument("-b", "--backend", type=str, default="serial", help="The backend to use for testing in pySPACE")
    return parser


def main(args=None):
    if args is None:
        args = sys.argv
    print("Start optimization..")
    parser = create_parser()
    arguments = parser.parse_args(args)
    with open(arguments.experiment, "rb") as file_:
        task = Task.from_yaml(file_)
    optimizer = optimizer_factory(task, arguments.backend)
    best_result = optimizer.optimize()
    print("Done..")
    print("Best result: %s" % best_result)



if __name__ == "__main__":
    main()
