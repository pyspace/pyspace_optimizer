import sys


class OutputRedirecter(object):

    def __init__(self, std_out, std_err):
        self.__stdout = std_out,
        self.__stderr = std_err
        self.__old_stdout = None
        self.__old_stderr = None

    def __enter__(self):
        self.__old_stdout = sys.stdout
        self.__old_stderr = sys.stderr
        sys.stderr = self.__stdout
        sys.stdout = self.__stderr

    # noinspection PyUnusedLocal
    def __exit__(self, *args, **kwargs):
        sys.sterr = self.__old_stderr
        sys.stdout = self.__old_stdout


class FileLikeLogger(object):
    def __init__(self, logger, log_level):
        self.__logger = logger
        self.__log_level = log_level

    def flush(self):
        pass

    def write(self, message):
        while message[-1] in ("\r", "\n"):
            # strip tailing newlines
            message = message[:-1]
        self.__logger.log(level=self.__log_level, msg=message)


class OutputLogger(object):

    def __init__(self, logger, log_level):
        self._logger = logger
        self._log_level = log_level
        self.__old_std_out = None
        self._old_std_err = None

    def __enter__(self):
        self.__old_std_out = sys.stdout
        self.__old_std_err = sys.stderr
        sys.stdout = FileLikeLogger(self._logger, self._log_level)
        sys.stderr = FileLikeLogger(self._logger, self._log_level)

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.__old_std_out
        sys.stderr = self.__old_std_err
