import builtins
import contextlib
import datetime
import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from functools import wraps



class Watcher:
    def __init__(self):
        self.buffers = {}
        self.logs = {}


    @contextlib.contextmanager
    def redirect_file_output(self, fname=None, mode='r', *args, **kwargs):
        if mode == 'w':
            if fname not in self.buffers:
                self.buffers[fname] = StringIO()
            fh = self.buffers[fname]
        else:
            fh = builtins.open(fname, mode, *args, **kwargs)

        try:
            yield fh
        finally:
            if mode != 'w':
                fh.close()

    def log(self, name):

        def log_wrapper(f):

            @wraps(f)
            def nested_f(*args, **kwargs):

                start_time = datetime.datetime.now()
                s = StringIO()

                # save function globals
                saved_function_context = f.__globals__.copy()

                # change open function behaviour to write to stringio
                f.__globals__.update({'open': self.redirect_file_output})

                with redirect_stdout(s):
                    return_values = f(*args, **kwargs)

                # restore default behaviour
                f.__globals__.update(saved_function_context)

                end_time = datetime.datetime.now()

                log_files = {fname: [s.strip() for s in b.getvalue().splitlines()]
                            for fname, b in self.buffers.items()}
                json_log = {'start time': str(start_time),
                            'end time': str(end_time),
                            'elapsed time': str(end_time - start_time),
                            'input values': 'args: {} kwargs: {}'.format(args, kwargs),
                            'function outputs': s.getvalue().splitlines(),
                            'log files outputs': log_files,
                            'return values': str(return_values)
                            }
                self.logs[name] = json_log
            return nested_f
        return log_wrapper

