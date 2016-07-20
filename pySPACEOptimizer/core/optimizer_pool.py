import threading
from multiprocessing.pool import Pool, Process, RUN, debug, CLOSE, TERMINATE


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

    DEFAULT_TIMEOUT = 1e100

    def __init__(self, processes=None, initializer=None, initargs=None):
        if initargs is None:
            initargs = ()
        super(OptimizerPool, self).__init__(processes=processes, initializer=initializer, initargs=initargs)

    #        signal.signal(signal.SIGTERM, self._handle_signal)
    #        signal.signal(signal.SIGINT, self._handle_signal)
    #        signal.signal(signal.SIGQUIT, self._handle_signal)

    def apply(self, func, args=None, kwds=None):
        assert self._state == RUN
        # Assert that .get gets a VERY LARGE timeout
        # as mentioned in http://bugs.python.org/issue8296
        # this is a bug in python which otherwise prevents signals from
        # being processed
        return self.apply_async(func=func,
                                args=args if args is not None else (),
                                kwds=kwds if kwds is not None else {}).get(timeout=self.DEFAULT_TIMEOUT)

    def map(self, func, iterable, chunksize=None):
        assert self._state == RUN
        # Assert that .get gets a VERY LARGE timeout
        # as mentioned in http://bugs.python.org/issue8296
        # this is a bug in python which otherwise prevents signals from
        # being processed
        return self.map_async(func, iterable, chunksize).get(timeout=self.DEFAULT_TIMEOUT)

    def join(self):
        debug('joining pool')
        assert self._state in (CLOSE, TERMINATE)
        self._worker_handler.join(timeout=self.DEFAULT_TIMEOUT)
        self._task_handler.join(timeout=self.DEFAULT_TIMEOUT)
        self._result_handler.join(timeout=self.DEFAULT_TIMEOUT)
        for p in self._pool:
            p.join(timeout=self.DEFAULT_TIMEOUT)

    @classmethod
    def _terminate_pool(cls, task_queue, in_queue, out_queue, pool,
                        worker_handler, task_handler, result_handler, cache):
        # this is guaranteed to only be called once
        debug('finalizing pool')

        worker_handler._state = TERMINATE
        task_handler._state = TERMINATE

        debug('helping task handler/workers to finish')
        cls._help_stuff_finish(in_queue, task_handler, len(pool))

        # We must wait for the worker handler to exit before terminating
        # workers because we don't want workers to be restarted behind our back.
        debug('joining worker handler')
        if threading.current_thread() is not worker_handler:
            worker_handler.join(1e100)

        # Terminate workers which haven't already finished.
        if pool and hasattr(pool[0], 'terminate'):
            debug('terminating workers')
            for p in pool:
                if p.exitcode is None:
                    p.terminate()
                    p.join(timeout=cls.DEFAULT_TIMEOUT)

        debug('joining task handler')
        if threading.current_thread() is not task_handler:
            task_handler.join(1e100)

        assert result_handler.is_alive() or len(cache) == 0

        result_handler._state = TERMINATE
        out_queue.put(None)  # sentinel

        debug('joining result handler')
        if threading.current_thread() is not result_handler:
            result_handler.join(1e100)

        if pool and hasattr(pool[0], 'terminate'):
            debug('joining pool workers')
            for p in pool:
                if p.is_alive():
                    # worker has not yet exited
                    debug('cleaning up worker %d' % p.pid)
                    p.join()

    def _handle_signal(self, *_):
        self.terminate()
        self.join()
