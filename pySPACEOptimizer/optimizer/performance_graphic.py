import abc
from collections import defaultdict
from matplotlib import pyplot


class PerformanceGraphic(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, window_size=1, file_path="performance.png"):
        self.__file_path = file_path
        self.__window_size = window_size
        self.__tids = defaultdict(lambda: [])
        self.__averages = defaultdict(lambda: [])
        self.__mean = defaultdict(lambda: 0)
        self.__bests = defaultdict(lambda: float("inf"))
        self.__current_indexes = defaultdict(lambda: 0)

    @abc.abstractmethod
    def _get_loss(self, pipeline, trial_number):
        raise NotImplementedError()

    @abc.abstractmethod
    def _number_of_trials(self, pipeline):
        raise NotImplementedError()

    def update(self, pipelines, number_of_evaluations):
        for pipeline in pipelines:
            number_of_trials = self._number_of_trials(pipeline)
            for i in range(self.__current_indexes[pipeline], self.__current_indexes[pipeline] + number_of_evaluations):
                current_loss = self._get_loss(pipeline, i)
                if number_of_trials > i and  current_loss < float("inf"):
                    # calculate the average
                    self.__mean[pipeline] += current_loss / self.__window_size
                    if i >= self.__window_size:
                        last_loss = self._get_loss(pipeline, i - self.__window_size)
                        if  last_loss < float("inf"):
                            self.__mean[pipeline] -= last_loss / self.__window_size
                        else:
                            self.__mean[pipeline] -= current_loss / self.__window_size
                        self.__tids[pipeline].append(i)
                        self.__averages[pipeline].append(self.__mean[pipeline])
                # And check the best
                if self.__bests[i] > current_loss:
                    self.__bests[i] = current_loss
            # Save the index
            self.__current_indexes[pipeline] += number_of_evaluations
            # Plot the results
            pyplot.title("Pipeline performance during optimization")
            pyplot.plot(self.__tids[pipeline], self.__averages[pipeline], label="%s" % pipeline)

        # and calculate the list of bests
        best = float("inf")
        bests = []
        for tid, tid_best in self.__bests.items():
            if tid_best < best:
                best = tid_best
                pyplot.annotate("%.3f" % best, xy=(tid, best),
                                textcoords="offset points", xytext=(1, 25),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3"))
            bests.append(best)
        pyplot.plot(self.__bests.keys(), bests, label="Best loss at trial")

        pyplot.xlabel("Trial number")
        pyplot.ylabel("Loss")
        pyplot.legend()
        pyplot.savefig(self.__file_path)
        # Clear the figure for next plot
        pyplot.clf()
