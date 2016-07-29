import copy
import os

from hyperopt import Trials, Domain, base, JOB_STATE_DONE

from pySPACE.missions.nodes.decorators import ChoiceParameter
from pySPACEOptimizer.framework.node_parameter_space import NodeParameterSpace

try:
    # noinspection PyCompatibility
    from cPickle import load, dump, HIGHEST_PROTOCOL
except ImportError:
    from pickle import load, dump, HIGHEST_PROTOCOL


class Trial(object):
    def __init__(self, trial, attachments):
        self.__trial = trial
        self.__attachments = attachments

    @property
    def id(self):
        return self.__trial["tid"]

    @property
    def loss(self):
        return self.__trial["result"]["loss"]

    def parameters(self, pipeline):
        parameters = base.spec_from_misc(self.__trial["misc"])
        new_pipeline_space = {}
        new_parameters = copy.copy(parameters)
        for node in pipeline.nodes:
            new_pipeline_space.update(NodeParameterSpace.parameter_space(node))
        for key, value in parameters.items():
            if key in new_pipeline_space:
                if isinstance(new_pipeline_space[key], ChoiceParameter):
                    new_parameters[key] = new_pipeline_space[key].choices[value]
                else:
                    new_parameters[key] = value
            else:
                try:
                    pipeline.logger.warn("Parameter '%s' was not found in the parameter space - skipping" % key)
                except IOError:
                    # Maybe we can't log. Ignore
                    pass
        return new_parameters

    @property
    def attachments(self):
        return self.__attachments

    def __getitem__(self, item):
        return self.__trial[item]


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
    ATTACHMENTS_NAME = "attachments.pickle"

    def __init__(self, trials_dir, fn, space, recreate=False, exp_key=None, refresh=True, rseed=None):
        self._trials_file = os.path.join(trials_dir, self.STORAGE_NAME)
        self._attachments_file = os.path.join(trials_dir, self.ATTACHMENTS_NAME)
        if recreate and os.path.isfile(self._trials_file):
            os.unlink(self._trials_file)
            os.unlink(self._attachments_file)
        super(PersistentTrials, self).__init__(exp_key=exp_key, refresh=False)
        # Load the last trials from the trials directory
        self._dynamic_trials = self._load_trials()
        self.attachments = self._load_attachments()
        self.__rseed = rseed if rseed is not None else 123
        # Now create the domain to store the model
        if "domain" in self.attachments:
            # Load the domain from the attachments
            self.__domain = self.attachments["domain"]
        else:
            # create a new domain and store it
            self.__domain = Domain(fn=fn, expr=space, workdir=trials_dir, rseed=self.__rseed)
            self.attachments["domain"] = self.__domain
        if refresh:
            self.refresh()

    def _load_attachments(self):
        if os.path.isfile(self._attachments_file):
            with open(self._attachments_file, "rb") as attachments_file:
                return load(attachments_file)
        else:
            # Don't throw any trials away
            return self.attachments

    def _store_attachments(self):
        with open(self._attachments_file, "wb") as attachments_file:
            dump(self.attachments, attachments_file)

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
        self._store_attachments()

        # and refresh the real trials
        super(PersistentTrials, self).refresh()

    def delete_all(self):
        # Remove the stored file
        try:
            os.unlink(self._trials_file)
            os.unlink(self._attachments_file)
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

    def _do_evaluate(self, trials):
        for trial in trials:
            evaluate_trial(domain=self.__domain, trials=self, trial=trial)
            yield trial

    def _evaluate(self, evaluations, pass_):
        # Get the trials to evaluate
        trials_to_evaluate = []
        # yield all already evaluated trials
        for trial in self._dynamic_trials[evaluations * (pass_ - 1):evaluations * pass_]:
            if trial["state"] == base.JOB_STATE_NEW:
                trials_to_evaluate.append(trial)
            else:
                yield trial
        # evaluate the trials that have to be done and yield the result
        for trial in self._do_evaluate(trials_to_evaluate):
            self._update_doc(trial=trial)
            yield trial

    def _enqueue_trials(self, algo, max_evals):
        n_to_enqueue = max_evals - len(self._trials)
        if n_to_enqueue > 0:
            new_ids = self.new_trial_ids(n_to_enqueue)
            new_trials = algo(new_ids=new_ids,
                              domain=self.__domain,
                              trials=self,
                              seed=self.__rseed)
            if new_trials is base.StopExperiment:
                return False
            else:
                assert len(new_ids) >= len(new_trials)
                if new_trials:
                    self.insert_trial_docs(new_trials)
                else:
                    return False
        return True

    def minimize(self, algo, evaluations, pass_):
        # Enqueue the trials
        if not self._enqueue_trials(algo=algo, max_evals=evaluations * pass_):
            raise StopIteration()

        # Do one minimization step and yield the result
        for trial in self._evaluate(evaluations=evaluations, pass_=pass_):
            # yield the result
            yield Trial(trial, self.trial_attachments(trial))
        # Refresh the trials to persist the changes
        self.refresh()

    def __getstate__(self):
        result = self.__dict__.copy()
        return result

    @property
    def best_trial(self):
        best_trial = super(PersistentTrials, self).best_trial
        return Trial(best_trial, self.trial_attachments(best_trial))

    @property
    def num_finished(self):
        return self.count_by_state_unsynced(JOB_STATE_DONE)

    def __getitem__(self, index):
        return Trial(self._dynamic_trials[index], self.trial_attachments(self._dynamic_trials[index]))

    def __iter__(self):
        for trial in self._dynamic_trials:
            yield Trial(trial, self.trial_attachments(trial))
