import signal
from multiprocessing.pool import Pool, Process, RUN, debug, CLOSE, TERMINATE

import sys


class NoDaemonProcess(Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
# noinspection PyAbstractClass
class OptimizerPool(Pool):
    Process = NoDaemonProcess

    DEFAULT_GET_TIMEOUT = 1e100

    def __init__(self, processes=None, initializer=None, initargs=None, maxtasksperchild=None):
        if initargs is None:
            initargs = ()
        super(OptimizerPool, self).__init__(processes=processes, initializer=initializer, initargs=initargs,
                                            maxtasksperchild=maxtasksperchild)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGQUIT, self._handle_signal)

    def apply(self, func, args=None, kwds=None):
        assert self._state == RUN
        # Assert that .get gets a VERY LARGE timeout
        # as mentioned in http://bugs.python.org/issue8296
        # this is a bug in python which otherwise prevents signals from
        # being processed
        return self.apply_async(func=func,
                                args=args if args is not None else (),
                                kwds=kwds if kwds is not None else {}).get(timeout=self.DEFAULT_GET_TIMEOUT)

    def map(self, func, iterable, chunksize=None):
        assert self._state == RUN
        # Assert that .get gets a VERY LARGE timeout
        # as mentioned in http://bugs.python.org/issue8296
        # this is a bug in python which otherwise prevents signals from
        # being processed
        return self.map_async(func, iterable, chunksize).get(timeout=self.DEFAULT_GET_TIMEOUT)

    def join(self):
        debug('joining pool')
        assert self._state in (CLOSE, TERMINATE)
        self._worker_handler.join(timeout=self.DEFAULT_GET_TIMEOUT)
        self._task_handler.join(timeout=self.DEFAULT_GET_TIMEOUT)
        self._result_handler.join(timeout=self.DEFAULT_GET_TIMEOUT)
        for p in self._pool:
            p.join(timeout=self.DEFAULT_GET_TIMEOUT)

    def _handle_signal(self, signal_, _):
        # Terminate all sub processes
        self.terminate()
        # And then exit this process
        sys.exit(signal_)
