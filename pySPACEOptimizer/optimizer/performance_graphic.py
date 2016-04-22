import abc
import logging
from collections import defaultdict
from matplotlib import pyplot


class PerformanceGraphic(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, window_size=1, file_path="performance.pdf"):
        self.__file_path = file_path
        self.__window_size = window_size
        self.__tids = defaultdict(lambda: [])
        self.__averages = defaultdict(lambda: [])
        self.__bests = defaultdict(lambda: float("inf"))
        self.__current_indexes = defaultdict(lambda: 0)
        self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

    @abc.abstractmethod
    def _get_loss(self, pipeline, trial_number):
        raise NotImplementedError()

    @abc.abstractmethod
    def _number_of_trials(self, pipeline):
        raise NotImplementedError()

    def update(self, pipelines, number_of_evaluations):
        figure = pyplot.figure(figsize=(11, 8), dpi=80)
        pyplot.xlabel("Trial number")
        pyplot.ylabel("Loss")

        for pipeline in pipelines:
            number_of_trials = self._number_of_trials(pipeline)
            for i in range(self.__current_indexes[pipeline], self.__current_indexes[pipeline] + number_of_evaluations):
                if number_of_trials > i:
                    current_loss = self._get_loss(pipeline, i)
                    if i >= self.__window_size:
                        mean = 0
                        number_of_points = 0
                        for x in range(i - self.__window_size + 1, i + 1):
                            loss = self._get_loss(pipeline, x)
                            if loss < float("inf"):
                                mean += loss
                                number_of_points += 1
                        self.__tids[pipeline].append(i)
                        if number_of_points > 0:
                            self.__averages[pipeline].append(mean / number_of_points)
                        else:
                            # No valid points inside the window,
                            # average must be infinitely high
                            self.__averages[pipeline].append(float("inf"))
                    # And check the best
                    if self.__bests[i] > current_loss:
                        self.__bests[i] = current_loss
                    self.__current_indexes[pipeline] += 1
                else:
                    break
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

        if len(pipelines) <= 4:
            # Plot only a legend if the number of pipelines is
            # at most 4, because otherwise we don't see anything from the graph
            pyplot.legend(fancybox=True, framealpha=0.3, fontsize="small")
        pyplot.savefig(self.__file_path, format="pdf", transparent=True)
        # Clear the figure for next plot
        pyplot.clf()
        pyplot.close(figure)
