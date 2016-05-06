import logging
import sys


class output_diverter(object):

    def __init__(self, std_out=None, std_err=None):
        self.__stdout = std_out
        self.__stderr = std_err
        self.__old_stdout = None
        self.__old_stderr = None

    def __enter__(self):
        self.__old_stdout = sys.stdout
        self.__old_stderr = sys.stderr
        if self.__stdout is not None:
            sys.stdout = self.__stdout
        if self.__stderr is not None:
            sys.stderr = self.__stderr

    # noinspection PyUnusedLocal
    def __exit__(self, *args, **kwargs):
        sys.stdout = self.__old_stdout
        sys.stderr = self.__old_stderr


class FileLikeLogger(object):
    def __init__(self, logger, log_level):
        self.__logger = logger
        self.__log_level = log_level

    def flush(self):
        pass

    def write(self, message):
        if self.__logger:
            while message and message[-1] in ("\r", "\n"):
                # strip tailing newlines
                message = message[:-1]
            self.__logger.log(level=self.__log_level, msg=message)


class output_logger(object):

    def __init__(self, std_out_logger, std_err_logger, std_out_log_level=logging.INFO, std_err_log_level=logging.ERROR):
        self._std_out_logger = std_out_logger
        self._std_out_log_level = std_out_log_level
        self._std_err_logger = std_err_logger
        self._std_err_log_level = std_err_log_level
        self.__old_std_out = None
        self.__old_std_err = None

    def __enter__(self):
        self.__old_std_out = sys.stdout
        self.__old_std_err = sys.stderr
        sys.stdout = FileLikeLogger(self._std_out_logger, self._std_out_log_level)
        sys.stderr = FileLikeLogger(self._std_err_logger, self._std_err_log_level)

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.__old_std_out
        sys.stderr = self.__old_std_err
