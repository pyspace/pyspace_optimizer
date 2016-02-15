from multiprocessing.pool import Pool, Process


class NoDaemonProcess(Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class OptimizerPool(Pool):
    Process = NoDaemonProcess

    def __reduce__(self):
        return (OptimizerPool.__init__, (self._processes,
                                         self._initializer,
                                         self._initargs,
                                         self._maxtasksperchild))
