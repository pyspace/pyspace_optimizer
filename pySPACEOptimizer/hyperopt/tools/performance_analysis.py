# noinspection PyPackageRequirements
import matplotlib
import os

import pySPACE
# noinspection PyPackageRequirements
from PyQt4 import QtGui, QtCore
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
        self.addItems([pipeline.replace("_", "-") for pipeline in pipelines.keys()])
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

        self.__artists = {pipeline: None for pipeline in pipelines.keys()}
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
            for trial in self.__trials[pipeline]:
                if trial.loss < float("inf"):
                    mean += trial.loss
                    number_of_points += 1
                if trial.id >= self.__average:
                    last_loss = self.__trials[pipeline][trial.id - self.__average].loss
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
                artist.set_alpha(0.05)
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
            # just for consistency, if called from the outside
            # set the average on the widget
            self.__average_widget.setText(unicode(average))
            self.__canvas.draw()
        except (ValueError, TypeError):
            pass


class PipelineTable(QtGui.QTableWidget):
    def __init__(self, pipelines, trials, row_selection_callback=None, parent=None):
        super(PipelineTable, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
        self.setMaximumHeight(300)
        self.setMinimumHeight(150)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.__trials = trials
        self.__pipelines = pipelines
        self.__selected_pipeline = None
        self.__row_selection_callback = row_selection_callback
        self.__save_error = QtGui.QMessageBox()
        self.__save_error.setIcon(QtGui.QMessageBox.Critical)
        self.__save_error.setWindowTitle("Error saving the YAML")
        self.__save_error.setText("YAML can't be saved.")
        self.__save_error.setInformativeText(self.tr("Error: The pipeline is missing from the experiment."
                                               "Therefore no trial can be saved"))
        # noinspection PyUnresolvedReferences
        self.itemSelectionChanged.connect(self.selection_changed)

    def save_trial(self):
        pipeline = self.__pipelines[self.__selected_pipeline]
        if pipeline is not None:
            # Open a file dialog and get the filename to save the result to
            file_name = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save YAML as..."), pySPACE.configuration.spec_dir,
                                                          self.tr("YAML Files (*.yaml);;All files (*)"))
            if file_name:
                if not file_name.split("."):
                    file_name = file_name + ".yaml"
                trial = self.__trials[self.__selected_pipeline][self.selectedItems()[0].row()]
                operation_spec = pipeline.operation_spec(trial.parameters(pipeline))
                with open(file_name, "wb") as save_file:
                    save_file.write(operation_spec["base_file"])
        else:
            self.__save_error.show()


    def selection_changed(self):
        if self.__row_selection_callback is not None:
            if self.selectedItems():
                self.__row_selection_callback(self.selectedItems()[0].row())
            else:
                self.__row_selection_callback(None)

    def display(self, pipeline):
        self.clear()
        if self.contextMenuPolicy() != QtCore.Qt.ActionsContextMenu:
            # Add the "save" action
            self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            save = QtGui.QAction("Save as YAML", self)
            # noinspection PyUnresolvedReferences
            save.triggered.connect(self.save_trial)
            self.addAction(save)

        if pipeline in self.__trials:
            if self.__trials[pipeline]:
                self.__selected_pipeline = pipeline
                pipeline_obj = self.__pipelines[pipeline]
                if pipeline_obj is not None:
                    parameter_names = self.__trials[pipeline][0].parameters(pipeline_obj).keys()
                else:
                    parameter_names = self.__trials[pipeline][0]["misc"]["vals"].keys()

                self.setColumnCount(len(parameter_names) + 1)
                self.setHorizontalHeaderLabels(["Loss"] + parameter_names)
                for trial in self.__trials[pipeline]:
                    if trial.id >= self.rowCount():
                        self.insertRow(trial.id)
                    self.setItem(trial.id, 0, QtGui.QTableWidgetItem("{loss:.3f}".format(loss=trial.loss)))
                    if pipeline_obj is not None:
                        parameters = trial.parameters(pipeline_obj)
                    else:
                        parameters = {key: value[0] for key, value in trial["misc"]["vals"].items()}
                    for i, parameter in enumerate(parameter_names, 1):
                        self.setItem(trial.id, i, QtGui.QTableWidgetItem("{parameter!s}".format(
                            parameter=parameters[parameter])))
                self.resizeRowsToContents()

    def select_trial(self, tid):
        if 0 <= tid < self.rowCount():
            self.selectRow(tid)


class PerformanceAnalysisWidget(QtGui.QWidget):
    def __init__(self, experiment, parent=None):
        super(PerformanceAnalysisWidget, self).__init__(parent)
        self.__experiment = experiment
        # Search for the pipelines
        self.__pipelines = {}
        self.__trials = {}
        if experiment is not None and os.path.isdir(experiment):
            for element in os.listdir(experiment):
                if os.path.isdir(os.path.join(experiment, element)):
                    self.__trials[element] = PersistentTrials(os.path.join(self.__experiment, element), recreate=False)
                    self.__pipelines[element] = self.__trials[element].attachments.get("pipeline", None)

        average = 1
        # Get the average according to the step size in the task
        for pipeline in self.__pipelines.values():
            if pipeline is not None:
                average = pipeline.configuration["evaluations_per_pass"]
                break

        # Create the widgets
        self.__list_view = PipelineList(pipelines=self.__pipelines, callback=self._change_pipeline, parent=self)
        self.__graph_view = PipelineGraph(pipelines=self.__pipelines, trials=self.__trials, average=average,
                                          pick_callback=self._pick_trial, parent=self)
        self.__table_view = PipelineTable(pipelines=self.__pipelines, trials=self.__trials,
                                          row_selection_callback=self._select_trial, parent=self)

        # Layout the widgets
        right_widget = QtGui.QWidget()
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
        self.setWindowTitle(self.tr("Optimizer performance analysis"))
        self._init_menu_and_status_bar()
        self.__central_widget = PerformanceAnalysisWidget(experiment, self)
        self.setCentralWidget(self.__central_widget)

    def _init_menu_and_status_bar(self):
        self.statusBar()
        open_action = QtGui.QAction(self.tr("&Open"), self)
        open_action.setShortcut("Alt+O")
        open_action.setStatusTip(self.tr("Open a new experiment"))
        # noinspection PyUnresolvedReferences
        open_action.triggered.connect(self._open_experiment)

        exit_action = QtGui.QAction(self.tr("&Exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip(self.tr("Exit the application"))
        # noinspection PyUnresolvedReferences
        exit_action.triggered.connect(QtGui.qApp.quit)

        menuBar = self.menuBar()
        file_menu = menuBar.addMenu(self.tr("&File"))
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)


    def _open_experiment(self):
        experiment = unicode(QtGui.QFileDialog.getExistingDirectory(self, self.tr("Select experiment"),
                                                            pySPACE.configuration.storage))
        if experiment:
            # Replace the central widget
            del self.__central_widget
            self.__central_widget = PerformanceAnalysisWidget(experiment=experiment, parent=self)
            self.setCentralWidget(self.__central_widget)


def create_parser():
    arg_parser = ArgumentParser(prog=__file__)
    arg_parser.add_argument("-c", "--config", type=str, default=None, help="The pySPACE configuration to use")
    arg_parser.add_argument("-e", "--experiment", type=str, default=None,
                            help="The path to the experiment results to analyse")
    return arg_parser


if __name__ == "__main__":
    import sys
    parser = create_parser()
    arguments, unknown_args = parser.parse_known_args(sys.argv[1:])
    if arguments.config:
        pySPACE.load_configuration(conf_file_name=arguments.config)
    app = QtGui.QApplication(unknown_args)
    main = PerformanceAnalysisMainWindow(experiment=arguments.experiment)
    main.show()
    sys.exit(app.exec_())
