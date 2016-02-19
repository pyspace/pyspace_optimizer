import multiprocessing
import os

from hyperopt import Trials, Domain, base

from pySPACEOptimizer.optimizer.optimizer_pool import OptimizerPool

try:
    from cPickle import load, dump, HIGHEST_PROTOCOL
except ImportError:
    from pickle import load, dump, HIGHEST_PROTOCOL


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


def evaluate_trial(domain, trials, number, trial):
    if trial['state'] == base.JOB_STATE_NEW:
        spec = base.spec_from_misc(trial['misc'])
        ctrl = base.Ctrl(trials, current_trial=trial)
        try:
            result = domain.evaluate(spec, ctrl)
        except Exception, e:
            trial['state'] = base.JOB_STATE_ERROR
            trial['misc']['error'] = (str(type(e)), str(e))
        else:
            trial['state'] = base.JOB_STATE_DONE
            trial['result'] = result
    return number, trial



class MultiprocessingPersistentTrials(PersistentTrials):

    async = False

    def __init__(self, trials_dir, exp_key=None, refresh=True):
        super(MultiprocessingPersistentTrials, self).__init__(trials_dir=trials_dir, exp_key=exp_key, refresh=refresh)

    def _update_doc(self, result):
        number, doc = result
        self._dynamic_trials[number] = doc
        self.refresh()

    def get_queue_len(self):
        return self.count_by_state_unsynced(base.JOB_STATE_NEW)

    def fmin(self, fn, space, algo, max_evals, rseed=123):
        domain = Domain(fn, space, rseed=rseed)
        qlen = self.get_queue_len()
        n_to_enqueue = max_evals - qlen
        if n_to_enqueue > 0:
            new_ids = self.new_trial_ids(n_to_enqueue)
            self.refresh()
            new_trials = algo(new_ids, domain, self)
            if new_trials is base.StopExperiment:
                return None
            else:
                assert len(new_ids) >= len(new_trials)
                if new_trials:
                    self.insert_trial_docs(new_trials)
                    self.refresh()
                else:
                    return None

        pool = OptimizerPool()
        for number, doc in zip(range(len(self._dynamic_trials)), self._dynamic_trials):
            pool.apply_async(evaluate_trial, args=(domain, self, number, doc), callback=self._update_doc)
        # Close the pool
        pool.close()

        # And wait for the workers to finish
        try:
            pool.join()
        except multiprocessing.TimeoutError:
            pool.terminate()
            pool.join()

        # Refresh and return the minimum
        self.refresh()
        return self.argmin