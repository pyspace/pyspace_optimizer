import os
import threading
from argparse import ArgumentParser

import matplotlib
from PyQt4 import QtGui
# Use the Qt-Backend
from collections import defaultdict

matplotlib.use("Qt4Agg")

# now import pyplot and the backend components
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
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
        self.addItems(pipelines)
        self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Expanding)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setMaximumWidth(200)
        self.__callback = callback
        # noinspection PyUnresolvedReferences
        self.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        if self.__callback is not None:
            self.__callback(unicode(self.selectedItems()[0].text()))


class PipelineGraph(QtGui.QWidget):
    def __init__(self, pipelines, trials, average=1, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.__figure = pyplot.Figure()
        self.__axes = self.__figure.add_subplot(111)
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

        self.__pipelines = pipelines
        self.__average = average
        self.__trials = trials
        self.__selected_pipeline = None
        self.__tids = {}
        self.__averages = {}
        self._calculate_plots()
        self._redraw()

    def _calculate_plots(self):
        for pipeline in self.__pipelines:
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

    def _redraw(self):
        self.__figure.clear()
        axes = self.__figure.add_subplot(111)
        std_alpha = 1.0 if self.__selected_pipeline is None else 0.2
        for pipeline in self.__pipelines:
            axes.plot(self.__tids[pipeline], self.__averages[pipeline],
                      alpha=1.0 if pipeline == self.__selected_pipeline else std_alpha,
                      figure=self.__figure)
        self.__canvas.draw()


    def select(self, pipeline):
        self.__selected_pipeline = pipeline
        self._redraw()

    def set_average(self, average):
        try:
            self.__average = int(average)
            self._calculate_plots()
            self._redraw()
        except (ValueError, TypeError):
            pass


class PipelineTable(QtGui.QTableWidget):
    def __init__(self, trials, parent=None):
        super(PipelineTable, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        self.setMaximumHeight(150)
        self.__trials = trials

    def display(self, pipeline):
        self.clear()
        self.setColumnCount(1)
        self.setHorizontalHeaderLabels(["Loss", "Parameters"])
        if pipeline in self.__trials:
            for trial in self.__trials[pipeline]:
                self.insertRow(trial.id)
                self.setItem(trial.id, 0, QtGui.QTableWidgetItem("{loss:.3f}".format(loss=trial.loss)))
                self.setItem(trial.id, 1, QtGui.QTableWidgetItem("TODO"))


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
        self.__graph_view = PipelineGraph(self.__pipelines, self.__trials, parent=self)
        self.__table_view = PipelineTable(self.__trials, parent=self)
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

    def _change_pipeline(self, pipeline):
        self.__table_view.display(pipeline)


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
