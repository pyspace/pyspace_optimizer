from argparse import ArgumentParser, FileType
from matplotlib import pyplot

from hyperopt import JOB_STATE_DONE
try:
    from cPickle import load
except ImportError:
    from pickle import load


def parse_arguments(args):
    parser = ArgumentParser()
    parser.add_argument("-t", "--trials", type=FileType("rb"), help="The path to the trials.pickle object that"
                                                                    "should be analysed", required=True)
    parser.add_argument("-s", "--step-size", type=int, default=1,
                        help="The number of evaluations done in one step (used for averaging one step)")
    parser.add_argument("-w", "--window-size", type=int, default=10,
                        help="The number of jobs to average with a moving window")
    return parser.parse_args(args)


def main(args):
    arguments = parse_arguments(args)
    trials = load(arguments.trials)

    # Calculate the average for each step and the best loss
    tids, steps, bests, averages, averages_tids = [], [], [], [], []
    sum_of_losses = 0
    num_of_losses = 0
    best = float("inf")
    for i in range(len(trials)):
        if trials[i]["state"] == JOB_STATE_DONE:
            # First append the X coordinate
            tids.append(trials[i]["tid"])

            # Then calculate the step average
            sum_of_losses += trials[i]["result"]["loss"]
            num_of_losses += 1
            if num_of_losses == arguments.step_size:
                steps.extend([sum_of_losses / arguments.step_size] * arguments.step_size)
                sum_of_losses = 0
                num_of_losses = 0

            # and the best
            if trials[i]["result"]["loss"] < best:
                best = trials[i]["result"]["loss"]
                pyplot.annotate("%.3f" % best, xy=(trials[i]["tid"], best),
                                textcoords="offset points", xytext=(1, 25),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3"))
            bests.append(best)

            # and the average
            if i >= arguments.window_size:
                mean = 0
                num_of_averages = 0
                for x in range(i - arguments.window_size + 1, i + 1):
                    loss = trials[x]["result"]["loss"]
                    if loss < float("inf"):
                        mean += loss
                        num_of_averages += 1
                averages_tids.append(i)
                if num_of_averages > 0:
                    averages.append(mean / num_of_averages)
                else:
                    # No valid points inside the window,
                    # average must be infinitely high
                    averages.append(float("inf"))

    # append last step
    if num_of_losses > 0:
        steps.extend([sum_of_losses / num_of_losses] * num_of_losses)

    # Plot the results
    pyplot.title("Performance of a pipeline during optimization")
    pyplot.plot(tids, steps, label="Average loss per step")
    pyplot.plot(tids, bests, label="Best loss at trial")
    pyplot.plot(averages_tids, averages, label="SMA of %d" % arguments.window_size)
    pyplot.xlabel("Trial number")
    pyplot.ylabel("Loss")
    pyplot.legend()
    pyplot.show(block=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
