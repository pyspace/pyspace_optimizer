from pySPACEOptimizer.optimizer.hyperopt_optimizer.persistent_trials import PersistentTrials
from pySPACEOptimizer.optimizer.performance_graphic import PerformanceGraphic


class HyperoptPerformanceGraphic(PerformanceGraphic):

    def _get_loss(self, pipeline, trial_number):
        trials = PersistentTrials(pipeline.base_result_dir)
        return trials[trial_number]["result"]["loss"]

    def _number_of_trials(self, pipeline):
        trials = PersistentTrials(pipeline.base_result_dir)
        return len(trials)
