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


    def log(self, name, redirect_files=False):
        def log_wrapper(f):
            @wraps(f)
            def nested_f(*args, **kwargs):
                if redirect_files:
                    # save function globals
                    saved_function_context = f.__globals__.copy()
                    # change open function behaviour to write to stringio
                    f.__globals__.update({'open': self.redirect_file_output})

                # creates stringio
                s = StringIO()

                start_time = datetime.datetime.now()
                # redirects function sys.stdout to stringio
                with redirect_stdout(s):
                    return_values = f(*args, **kwargs)

                end_time = datetime.datetime.now()

                if redirect_files:
                    # restore default behaviour
                    f.__globals__.update(saved_function_context)

                    # parse text written to log files inside function
                    log_files = {fname: [s.strip() for s in b.getvalue().splitlines()]
                                for fname, b in self.buffers.items()}
                else:
                    log_files = None

                json_log = {'start time': str(start_time),
                            'end time': str(end_time),
                            'elapsed time': str(end_time - start_time),
                            'input values': 'args: {} kwargs: {}'.format(args, kwargs),
                            'prints': s.getvalue().splitlines(),
                            'log files outputs': log_files,
                            'return values': str(return_values)
                            }

                execution_name = '{} ({})'.format(name, start_time)
                self.logs[execution_name] = json_log
            return nested_f
        return log_wrapper

