#retry decorator, exceptions to retry on, and retry on failure
from functools import wraps
import multiprocessing
import time


def retry(tries, exceptions=Exception, delay=0, backoff=1, logger=None):
    """
    Retry calling the decorated function using an exponential backoff.

    delay sets the initial delay between retries in seconds.
    backoff sets the factor by which the delay should lengthen after each failure.
    tries is the maximum number of attempts, delay is the initial delay in seconds,
    backoff is the factor by which the delay should be lengthened after a failure,
    and jitter can be added by setting jitter to a float.

    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param exceptions: the exception to check. may be a tuple of exceptions to check
    :type exceptions: Exception or tuple
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier
    :type backoff: int
    :param logger: logger to use
    :type logger: logging.Logger
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry


class Process(multiprocessing.Process):
    """
    Class which returns child Exceptions to Parent.
    https://stackoverflow.com/a/33599967/4992248
    """

    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self._parent_conn_result, self._child_conn_result = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            result = None
            if self._target:
                result = self._target(*self._args, **self._kwargs)

            self._child_conn_result.send(result)
            self._child_conn.send(None)
        except Exception as e:
            tb = e.__traceback__
            self._child_conn.send((str(e), str(tb)))
            # raise e  # You can still rise this exception if you need to

    @property
    def exception(self):
        if self._parent_conn.poll():
            self._exception = self._parent_conn.recv()
        return self._exception
    
    @property
    def result(self):
        if self._parent_conn_result.poll():
            return self._parent_conn_result.recv()
        return None