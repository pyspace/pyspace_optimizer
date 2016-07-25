import logging
import threading
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('pdf', warn=True, force=True)
    from matplotlib import pyplot

    class PerformanceGraphic(threading.Thread):

        def __init__(self, file_path="performance.pdf"):
            super(PerformanceGraphic, self).__init__(name="PerformanceGraphic")
            self.__file_path = file_path
            self._logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
            self.__pipelines = defaultdict(lambda: [])
            self.__number_of_trials = defaultdict(lambda: 0)
            self.__lock = threading.Lock()
            self.__stopped = threading.Event()

        def add(self, pipeline, id_, loss):
            with self.__lock:
                if id_ > self.__number_of_trials[pipeline]:
                    self.__number_of_trials[pipeline] = id_

                path = self.__pipelines[pipeline]
                if not path:
                    path.append((id_, loss))
                elif path[-1][0] < id_:
                    # The trial is at the end of the path
                    # simply check the last segment
                    if path[-1][1] > loss:
                        path.append((id_, loss))
                else:
                    # It is somewhere inside the path
                    # search for it an update the path
                    # from there on
                    for i, (tid, tloss) in enumerate(path):
                        if tid > id_ and path[i][1] > loss:
                            path.insert(i, (id_, loss))
                        elif tid > id_ and tloss > loss:
                            path[i][1] = loss

        def __update(self):
            figure = pyplot.figure(figsize=(11, 8), dpi=80)
            figure.set_tight_layout(True)
            pyplot.xlabel("Trial number")
            pyplot.ylabel("Loss")
            pyplot.title("Processing pipeline performance during optimization")

            global_min = (0, float("inf"))
            with self.__lock:
                number_of_pipelines = len(self.__pipelines)
                for pipeline, path in self.__pipelines.items():
                    # Interpolate the path
                    path_index = 0
                    plot_path = []
                    for i in range(self.__number_of_trials[pipeline] + 1):
                        if path_index + 1 < len(path) and path[path_index + 1][0] <= i:
                            path_index += 1
                        id_, loss = path[path_index]
                        plot_path.append(loss)
                        if loss < global_min[1]:
                            global_min = (id_, loss)
                    # Plot the results
                    pyplot.plot(range(len(plot_path)), plot_path, label="%s" % pipeline)
            # And annotate the global minimum
            pyplot.annotate("%.3f" % global_min[1], xy=global_min, textcoords="offset points", xytext=(1, 25),
                            arrowprops=dict(arrowstyle="->", connectionstyle="arc3"))

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
