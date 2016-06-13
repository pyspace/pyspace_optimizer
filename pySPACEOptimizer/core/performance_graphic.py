import logging
import threading
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('pdf', warn=True, force=True)
    from matplotlib import pyplot

    class PerformanceGraphic(threading.Thread):

        def __init__(self, window_size=1, file_path="performance.pdf"):
            super(PerformanceGraphic, self).__init__(name="PerformanceGraphic")
            self.__file_path = file_path
            self.__window_size = window_size
            self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
            self.__trials = defaultdict(lambda: [])
            self.__tids = defaultdict(lambda: [])
            self.__averages = defaultdict(lambda: [])
            self.__means = defaultdict(lambda: 0)
            self.__number_of_points = defaultdict(lambda: 0)
            self.__bests = defaultdict(lambda: float("inf"))
            self.__current_indexes = defaultdict(lambda: 0)
            self.__lock = threading.Lock()
            self.__stopped = threading.Event()

        def add(self, pipeline, id_, loss):
            with self.__lock:
                trials = self.__trials[pipeline]
                if len(trials) <= id_:
                    trials.extend([float("inf") for _ in range(len(trials), id_ + 1)])
                trials[id_] = loss

        def __update(self):
            figure = pyplot.figure(figsize=(11, 8), dpi=80)
            figure.set_tight_layout(True)
            pyplot.xlabel("Trial number")
            pyplot.ylabel("Loss")

            with self.__lock:
                number_of_pipelines = len(self.__trials.keys())
                for pipeline, trials in self.__trials.items():
                    if self.__current_indexes[pipeline] < len(trials):
                        for i in range(self.__current_indexes[pipeline], len(trials)):
                            current_loss = trials[i]
                            if current_loss < float("inf"):
                                self.__means[pipeline] += current_loss
                                self.__number_of_points[pipeline] += 1

                            if i >= self.__window_size:
                                last_loss = trials[i - self.__window_size]
                                if last_loss < float("inf"):
                                    self.__means[pipeline] -= last_loss
                                    self.__number_of_points[pipeline] -= 1
                                self.__tids[pipeline].append(i)
                                if self.__number_of_points[pipeline] > 0:
                                    self.__averages[pipeline].append(self.__means[pipeline] /
                                                                     self.__number_of_points[pipeline])
                                else:
                                    # No valid points inside the window,
                                    # average must be infinitely high
                                    self.__averages[pipeline].append(float("inf"))
                            # And check the best
                            if self.__bests[i] > current_loss:
                                self.__bests[i] = current_loss
                            self.__current_indexes[pipeline] += 1
                    # Plot the results
                    pyplot.title("NodeChainParameterSpace performance during optimization")
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

            if number_of_pipelines <= 4:
                # Plot only a legend if the number of pipelines is
                # at most 4, because otherwise we don't see anything from the graph
                pyplot.legend(fancybox=True, framealpha=0.3, fontsize="small")
            pyplot.savefig(self.__file_path, format="pdf", transparent=True)
            # Clear the figure for next plot
            pyplot.clf()
            pyplot.close(figure)

        def run(self):
            while not self.__stopped.isSet():
                # Wait one minute
                self.__stopped.wait(timeout=60)
                # Update the performance graphic
                self.__update()

        def stop(self):
            self.__stopped.set()

except ImportError:
    # No matplotlib installed
    # create a dummy class
    class PerformanceGraphic(object):
        def add(self, pipeline, id_, loss):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def join(self):
            pass
