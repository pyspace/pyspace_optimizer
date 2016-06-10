# noinspection PyPackageRequirements
import matplotlib
import os
# noinspection PyPackageRequirements
from PyQt4 import QtGui
from argparse import ArgumentParser

# Use the Qt-Backend

matplotlib.use("Qt4Agg")

# now import pyplot and the backend components
# noinspection PyPackageRequirements
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
# noinspection PyPackageRequirements
from matplotlib import pyplot
from pySPACEOptimizer.hyperopt.persistent_trials import PersistentTrials


class NoValidExperiment(Exception):
    def __init__(self, experiment):
        self.__experiment = experiment

    def __str__(self):
        return u"'{experiment!s}' is not a valid experiment".format(experiment=self.__experiment)


class PipelineList(QtGui.QListWidget):
    def __init__(self, pipelines, callback, parent=None):
        super(PipelineList, self).__init__(parent)
        self.addItems([pipeline.replace("_", "-") for pipeline in pipelines])
        self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Expanding)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setMaximumWidth(200)
        self.__callback = callback
        # noinspection PyUnresolvedReferences
        self.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        if self.__callback is not None:
            self.__callback(unicode(self.selectedItems()[0].text().replace("-", "_")))


class PipelineGraph(QtGui.QWidget):
    def __init__(self, pipelines, trials, average=1, pick_callback=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.__figure = pyplot.Figure()
        self.__figure.set_tight_layout(True)
        self.__axes = self.__figure.add_subplot(111)
        self.__axes.set_xlabel("Trial")
        self.__axes.set_ylabel("Loss")
        self.__axes.set_title("Performance analysis")
        self.__canvas = FigureCanvasQTAgg(self.__figure)
        self.__canvas.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.__nav_bar = NavigationToolbar2QT(self.__canvas, None)
        self.__average_widget = QtGui.QLineEdit()
        self.__average_widget.setText(unicode(average))
        self.__average_widget.setMaximumWidth(60)
        self.__average_widget.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        # noinspection PyUnresolvedReferences
        self.__average_widget.textChanged.connect(self.set_average)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.__canvas)
        nav_bar_container = QtGui.QWidget()
        nav_bar_container.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.__nav_bar)
        hbox.addWidget(self.__average_widget)
        nav_bar_container.setLayout(hbox)
        vbox.addWidget(nav_bar_container)
        self.setLayout(vbox)

        self.__artists = {pipeline: None for pipeline in pipelines}
        self.__selected_pipeline = None
        self.__mouse_artist = None
        self.__trial_artist = None
        self.__average = average
        self.__trials = trials
        self.__tids = {}
        self.__averages = {}
        self.__pick_callback = pick_callback
        self.__mouse_id = None
        self.__mouse_x = None
        self.__pick_id = None
        self._calculate_plots()

    def _calculate_plots(self):
        for pipeline in self.__artists.keys():
            mean = 0
            number_of_points = 0
            self.__averages[pipeline] = []
            self.__tids[pipeline] = []
            trials = [None] * len(self.__trials[pipeline])
            for trial in self.__trials[pipeline]:
                trials[trial.id] = trial

            for trial in trials:
                if trial.loss < float("inf"):
                    mean += trial.loss
                    number_of_points += 1
                if trial.id >= self.__average:
                    last_loss = trials[trial.id - self.__average].loss
                    if last_loss < float("inf"):
                        mean -= last_loss
                        number_of_points -= 1
                    self.__tids[pipeline].append(trial.id)
                    if number_of_points > 0:
                        self.__averages[pipeline].append(mean / number_of_points)
                    else:
                        # No valid points inside the window,
                        # average must be infinitely high
                        self.__averages[pipeline].append(float("inf"))
            if self.__artists[pipeline] is None:
                self.__artists[pipeline] = self.__axes.plot(self.__tids[pipeline], self.__averages[pipeline],
                                                            label=pipeline.replace("_", "-"))[0]
            else:
                self.__artists[pipeline].set_data([self.__tids[pipeline], self.__averages[pipeline]])

    def __handle_pick(self, event):
        if self.__pick_callback is not None:
            self.__pick_callback(int(event.xdata))

    def _move_mouse(self, event):
        pipeline_data = self.__averages[self.__selected_pipeline]
        if event.xdata is not None and self.__average <= event.xdata < len(pipeline_data) + self.__average:
            x = int(event.xdata)
            if self.__mouse_x != x:
                self.__mouse_x = x
                index = x - self.__average
                y = pipeline_data[index]
                if self.__mouse_artist is None:
                    self.__mouse_artist = self.__axes.plot(x, y, marker="D", scalex=False, scaley=False,
                                                           label="_mouse_marker")[0]
                else:
                    self.__mouse_artist.set_data([x, y])
                self.__mouse_artist.set_visible(True)
                self.__canvas.draw()

    def select_pipeline(self, pipeline):
        self.__selected_pipeline = pipeline
        for p, artist in self.__artists.items():
            if p == pipeline:
                artist.set_alpha(1)
            else:
                artist.set_alpha(0.1)
        if pipeline is not None:
            # Register for the mouse move event
            self.__mouse_id = self.__canvas.mpl_connect("motion_notify_event", self._move_mouse)
            # And for the pick event
            self.__pick_id = self.__canvas.mpl_connect("button_release_event", self.__handle_pick)
        else:
            self.__canvas.mpl_disconnect(self.__mouse_id)
            self.__canvas.mpl_disconnect(self.__pick_id)
        if self.__mouse_artist is not None:
            self.__mouse_artist.set_visible(False)
        if self.__trial_artist is not None:
            self.__trial_artist.set_visible(False)
        self.__canvas.draw()

    def select_trial(self, tid):
        if tid >= self.__average:
            index = tid - self.__average
            y = self.__averages[self.__selected_pipeline][index]
            if self.__trial_artist is None:
                self.__trial_artist = self.__axes.plot(tid, y, marker="D", scalex=False, scaley=False,
                                                       label="_selected_trial")[0]
            else:
                self.__trial_artist.set_data([tid, y])
            self.__trial_artist.set_visible(True)
            self.__canvas.draw()

    def set_average(self, average):
        try:
            self.__average = int(average)
            self._calculate_plots()
            if self.__mouse_artist is not None:
                self.__mouse_artist.set_visible(False)
            if self.__trial_artist is not None:
                self.__trial_artist.set_visible(False)
            self.__canvas.draw()
        except (ValueError, TypeError):
            pass


class PipelineTable(QtGui.QTableWidget):
    def __init__(self, trials, row_selection_callback=None, parent=None):
        super(PipelineTable, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
        self.setMaximumHeight(300)
        self.setMinimumHeight(150)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.__trials = trials
        self.__row_selection_callback = row_selection_callback
        # noinspection PyUnresolvedReferences
        self.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        if self.__row_selection_callback is not None:
            if self.selectedItems():
                self.__row_selection_callback(self.selectedItems()[0].row())
            else:
                self.__row_selection_callback(None)

    def display(self, pipeline):
        self.clear()
        number_of_parameters = len(self.__trials[pipeline][0]["misc"]["vals"])
        self.setColumnCount(number_of_parameters + 1)
        self.setHorizontalHeaderLabels(["Loss"] + self.__trials[pipeline][0]["misc"]["vals"].keys())
        if pipeline in self.__trials:
            for trial in self.__trials[pipeline]:
                if trial.id >= self.rowCount():
                    self.insertRow(trial.id)
                self.setItem(trial.id, 0, QtGui.QTableWidgetItem("{loss:.3f}".format(loss=trial.loss)))
                for i, value in enumerate(trial["misc"]["vals"].values(), 1):
                    self.setItem(trial.id, i, QtGui.QTableWidgetItem("{parameter!s}".format(parameter=value[0])))
                self.resizeRowToContents(trial.id)

    def select_trial(self, tid):
        if 0 <= tid < self.rowCount():
            self.selectRow(tid)


class PerformanceAnalysisWidget(QtGui.QWidget):
    def __init__(self, experiment, parent=None):
        super(PerformanceAnalysisWidget, self).__init__(parent)
        self.__experiment = experiment
        # Search for the pipelines
        self.__pipelines = []
        self.__trials = {}
        if experiment is not None and os.path.isdir(experiment):
            for element in os.listdir(experiment):
                if os.path.isdir(os.path.join(experiment, element)):
                    self.__pipelines.append(element)
                    self.__trials[element] = PersistentTrials(os.path.join(self.__experiment, element), recreate=False)

        # Create the widgets
        self.__list_view = PipelineList(self.__pipelines, self._change_pipeline, self)
        self.__graph_view = PipelineGraph(self.__pipelines, self.__trials, pick_callback=self._pick_trial, parent=self)
        self.__table_view = PipelineTable(self.__trials, self._select_trial, parent=self)
        right_widget = QtGui.QWidget()

        # Layout the widgets
        main_layout = QtGui.QHBoxLayout()
        main_layout.addWidget(self.__list_view)
        right_layout = QtGui.QVBoxLayout()
        right_widget.setLayout(right_layout)
        right_layout.addWidget(self.__graph_view)
        right_layout.addWidget(self.__table_view)
        main_layout.addWidget(right_widget)
        self.setLayout(main_layout)

    def _select_trial(self, tid):
        self.__graph_view.select_trial(tid)

    def _change_pipeline(self, pipeline):
        self.__graph_view.select_pipeline(pipeline)
        self.__table_view.display(pipeline)

    def _pick_trial(self, tid):
        self.__table_view.select_trial(tid)


class PerformanceAnalysisMainWindow(QtGui.QMainWindow):
    def __init__(self, experiment=None, parent=None):
        super(PerformanceAnalysisMainWindow, self).__init__(parent)
        self.resize(1024, 768)
        self.setWindowTitle("Optimizer performance analysis")
        self.__central_widget = PerformanceAnalysisWidget(experiment, self)
        self.setCentralWidget(self.__central_widget)


def create_parser():
    arg_parser = ArgumentParser(prog=__file__)
    arg_parser.add_argument("-e", "--experiment", type=str, default=None,
                            help="The path to the experiment results to analyse")
    return arg_parser


if __name__ == "__main__":
    import sys
    parser = create_parser()
    arguments, unknown_args = parser.parse_known_args(sys.argv[1:])
    app = QtGui.QApplication(unknown_args)
    main = PerformanceAnalysisMainWindow(experiment=arguments.experiment)
    main.show()
    sys.exit(app.exec_())
