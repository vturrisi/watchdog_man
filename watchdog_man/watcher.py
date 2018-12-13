import builtins
import contextlib
import datetime
import json
import sys
from contextlib import redirect_stdout
from functools import wraps
from io import StringIO
import warnings

import telegram


class TelegramException(ValueError):
    pass


class Watcher:
    def __init__(self, telegram_token=None):
        self.buffers = {}
        self.logs = {}
        self.telegram_token = telegram_token

    @contextlib.contextmanager
    def redirect_file_output(self, fname=None, mode='r', *args, **kwargs):
        if mode == 'w':
            # create a stringio for each file
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

    def log(self, name, collect_print=False, collect_files=False):
        def log_wrapper(f):
            @wraps(f)
            def nested_f(*args, **kwargs):
                if collect_files:
                    # save function globals
                    saved_function_context = f.__globals__.copy()
                    # change open function behaviour to write to stringio
                    f.__globals__.update({'open': self.redirect_file_output})

                start_time = datetime.datetime.now()
                # redirects function sys.stdout to stringio
                if collect_print:
                    # create stringio
                    sio = StringIO()
                    # redirect stdout to stringio
                    with redirect_stdout(sio):
                        return_values = f(*args, **kwargs)
                    print_data = sio.getvalue().splitlines()
                else:
                    return_values = f(*args, **kwargs)
                    print_data = None

                end_time = datetime.datetime.now()

                if collect_files:
                    # restore default behaviour
                    f.__globals__.update(saved_function_context)
                    # parse text written to log files inside function
                    files_data = {fname: [s.strip() for s in b.getvalue().splitlines()]
                                  for fname, b in self.buffers.items()}
                else:
                    files_data = None

                json_log = {'start time': str(start_time),
                            'end time': str(end_time),
                            'elapsed time': str(end_time - start_time),
                            'input values': 'args: {} kwargs: {}'.format(args, kwargs),
                            'prints': print_data,
                            'log files outputs': files_data,
                            'return values': str(return_values)
                            }

                execution_name = '{} ({})'.format(name, start_time)
                self.logs[execution_name] = json_log

                return return_values

            return nested_f

        return log_wrapper


    def notify_via_telegram(self, name, chat_id):
        def log_wrapper(f):
            @wraps(f)
            def nested_f(*args, **kwargs):
                try:
                    bot = telegram.Bot(token=self.telegram_token)
                except telegram.error.InvalidToken:
                    msg = 'Unable to create a telegram bot. Check if token exists.'
                    raise TelegramException(msg)

                start_time = datetime.datetime.now()

                return_values = f(*args, **kwargs)

                end_time = datetime.datetime.now()

                elapsed_time = end_time - start_time

                str_args = name, end_time, elapsed_time
                text = '{} finished running at {} (elapsed time {})'.format(*str_args)

                # check if something happend and raise a wanring
                # not raising error to allow for the experiment to finish
                try:
                    bot.sendMessage(chat_id=chat_id, text=text)
                except telegram.error.BadRequest as e:
                    msg = 'Unable to find chat with id {}.'.format(chat_id)
                    warnings.warn(msg, UserWarning)
                except telegram.error.Unauthorized:
                    msg = 'Unauthorized access (may be related to token).'
                    warnings.warn(msg, UserWarning)


                return return_values

            return nested_f

        return log_wrapper
