import os
import time

from hyperopt import Trials, Domain, base, JOB_STATE_NEW, JOB_STATE_DONE

from pySPACE.missions.nodes.decorators import ChoiceParameter
from pySPACEOptimizer.optimizer.optimizer_pool import OptimizerPool
from pySPACEOptimizer.pipelines import PipelineNode

try:
    # noinspection PyCompatibility
    from cPickle import load, dump, HIGHEST_PROTOCOL
except ImportError:
    from pickle import load, dump, HIGHEST_PROTOCOL


class Trial(object):
    def __init__(self, loss, parameters):
        self.__loss = loss
        self.__parameters = parameters

    @property
    def loss(self):
        return self.__loss

    def parameters(self, pipeline):
        new_pipeline_space = {}
        new_parameters = self.__parameters
        for node in pipeline.nodes:
            new_pipeline_space.update(PipelineNode.parameter_space(node))

        for key, value in self.__parameters.items():
            if isinstance(new_pipeline_space[key], ChoiceParameter):
                new_parameters[key] = new_pipeline_space[key].choices[value]
            else:
                new_parameters[key] = value
        return new_parameters


def evaluate_trial(domain, trials, trial):
    if trial["state"] == base.JOB_STATE_NEW:
        spec = base.spec_from_misc(trial['misc'])
        ctrl = base.Ctrl(trials, current_trial=trial)
        try:
            result = domain.evaluate(spec, ctrl)
        except Exception as e:
            trial['state'] = base.JOB_STATE_ERROR
            trial['misc']['error'] = (str(type(e)), str(e))
        else:
            trial['state'] = base.JOB_STATE_DONE
            trial['result'] = result
    return trial


# noinspection PyAbstractClass
class PersistentTrials(Trials):

    STORAGE_NAME = "trials.pickle"

    def __init__(self, trials_dir, exp_key=None, refresh=True):
        self._trials_file = os.path.join(trials_dir, self.STORAGE_NAME)
        super(PersistentTrials, self).__init__(exp_key=exp_key, refresh=False)
        # Load the last trials from the trials directory
        self._dynamic_trials = self._load_trials()
        if refresh:
            self.refresh()

    def _load_trials(self):
        if os.path.isfile(self._trials_file):
            with open(self._trials_file, "rb") as trials_file:
                return load(trials_file)
        else:
            # Don't throw any trials away
            return self._dynamic_trials

    def _store_trials(self):
        with open(self._trials_file, "wb") as trials_file:
            dump(self._dynamic_trials, trials_file)

    def refresh(self):
        # Store the trials
        self._store_trials()

        # and refresh the real trials
        super(PersistentTrials, self).refresh()

    def delete_all(self):
        # Remove the stored file
        try:
            os.unlink(self._trials_file)
        except (IOError, OSError):
            pass
        # and restore the state of the trials object
        return super(PersistentTrials, self).delete_all()

    def count_by_state_unsynced(self, job_state):
        """
        Return trial counts that count_by_state_synced would return if we
        called refresh() first.

        :param job_state: The state of the job to count
        :type job_state: basestring
        """
        trials = self._load_trials()
        if self._exp_key is not None:
            exp_trials = [tt for tt in trials if tt['exp_key'] == self._exp_key]
        else:
            exp_trials = trials
        return self.count_by_state_synced(job_state, trials=exp_trials)

    def _sorted_trials(self):
        # sort them in the following order:
        # JOB_STATUS_ERROR, JOB_STATUS_DONE, JOB_STATUS_RUNNING, JOB_STATUS_NEW
        def get_state(item):
            return item["state"]
        return sorted(self._dynamic_trials, key=get_state, reverse=True)

    def _update_doc(self, trial):
        self._dynamic_trials[trial["tid"]] = trial

    def _do_evaluate(self, domain, trials):
        for trial in trials:
            evaluate_trial(domain=domain, trials=self, trial=trial)
            yield trial

    def _evaluate(self, domain):
        # Get the trials to evaluate
        trials = [trial for trial in self._dynamic_trials if trial["state"] == JOB_STATE_NEW]
        for trial in self._do_evaluate(domain=domain, trials=trials):
            self._update_doc(trial=trial)
            yield trial

    def _enqueue_trials(self, domain, algo, max_evals, rseed):
        n_to_enqueue = max_evals - len(self._trials)
        if n_to_enqueue > 0:
            new_ids = self.new_trial_ids(n_to_enqueue)
            new_trials = algo(new_ids=new_ids,
                              domain=domain,
                              trials=self,
                              seed=rseed)
            if new_trials is base.StopExperiment:
                return False
            else:
                assert len(new_ids) >= len(new_trials)
                if new_trials:
                    self.insert_trial_docs(new_trials)
                else:
                    return False
        return True

    def minimize(self, fn, space, algo, max_evals, rseed=123):
        domain = Domain(fn, space, rseed=rseed)
        # Enqueue the trials
        if not self._enqueue_trials(domain=domain, algo=algo, max_evals=max_evals, rseed=rseed):
            raise StopIteration()

        # Do one minimization step and yield the result
        for trial in self._evaluate(domain=domain):
            # yield the result
            yield Trial(trial["result"]["loss"], base.spec_from_misc(trial["misc"]))
        # Refresh the trials to persist the changes
        self.refresh()

    def fmin(self, fn, space, algo, max_evals, rseed=123):
        # Do all minimization steps
        while self.minimize(fn=fn, space=space, algo=algo, max_evals=max_evals, rseed=rseed):
            pass

        # Return the best result
        return self.argmin

    def __getstate__(self):
        result = self.__dict__.copy()
        return result

    @property
    def best_trial(self):
        best_trial = super(PersistentTrials, self).best_trial
        return Trial(best_trial["result"]["loss"], base.spec_from_misc(best_trial["misc"]))

    @property
    def num_finished(self):
        return self.count_by_state_unsynced(JOB_STATE_DONE)


def trials_wrapper(args):
    return evaluate_trial(*args)


# noinspection PyAbstractClass
class MultiprocessingPersistentTrials(PersistentTrials):

    async = False

    def _do_evaluate(self, domain, trials):
        # Every worker just has to handle one task per default
        pool = OptimizerPool()

        # Create the arguments passed to the evaluation method
        args = [(domain, self, trial) for trial in trials]

        def _yield_args():
            for arg in args:
                yield arg
                # We need to sleep at least one second between two evaluations,
                # because pySPACE names the result folders with timestamps
                time.sleep(1)

        # noinspection PyProtectedMember
        chunksize = int(len(args) / pool._processes) if len(args) > pool._processes else 1

        # noinspection PyBroadException
        try:
            for trial in pool.imap_unordered(trials_wrapper, iterable=_yield_args(), chunksize=chunksize):
                yield trial
            # Close the pool
            pool.close()
        except:
            pool.terminate()
        finally:
            pool.join()
