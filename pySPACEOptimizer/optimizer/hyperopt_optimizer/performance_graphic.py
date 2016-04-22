from pySPACEOptimizer.optimizer.hyperopt_optimizer.persistent_trials import PersistentTrials
from pySPACEOptimizer.optimizer.performance_graphic import PerformanceGraphic


class HyperoptPerformanceGraphic(PerformanceGraphic):

    def _get_loss(self, pipeline, trial_number):
        try:
            trials = PersistentTrials(pipeline.base_result_dir)
            return trials[trial_number]["result"]["loss"]
        except IOError, e:
            self._logger.error(e.strerror)
            return float("inf")

    def _number_of_trials(self, pipeline):
        try:
            trials = PersistentTrials(pipeline.base_result_dir)
            return len(trials)
        except IOError, e:
            self._logger.error(e.strerror)
            return 0
