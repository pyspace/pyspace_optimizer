#!/bin/env python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from pySPACEOptimizer.configuration import Configuration
from pySPACEOptimizer.optimizer import get_optimizer


def create_parser():
    # TODO: Description and usage
    parser = ArgumentParser()
    parser.add_argument("-e", "--experiment", type=str, help="The path to an experiment description in YAML format")
    parser.add_argument("-b", "--backend", type=str, default="serial", help="The backend to use for testing in pySPACE")
    return parser


def main(args):
    parser = create_parser()
    arguments = parser.parse_args(args)
    with open(arguments.experiment, "rb") as file_:
        experiment = Configuration.from_yaml(file_)
    optimizer = get_optimizer(experiment.optimizer)(experiment, arguments.backend)
    return optimizer.optimize()


if __name__ == "__main__":
    import sys
    print("Start optimization..")
    best_result = main(sys.argv)
    print("Done..")
    print("Best result: %s" % best_result)
