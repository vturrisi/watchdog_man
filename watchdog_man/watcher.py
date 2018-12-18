import builtins
import contextlib
import datetime
import json
import os
import sys
import warnings
from contextlib import redirect_stdout, suppress
from functools import wraps
from io import StringIO

import telegram


class TelegramException(ValueError):
    pass


class Watcher:
    '''
    Base class for watchdog_man. A single watcher is capable of loging multiple functions.

    args:
        - auto_save_logs (boolean): automatically save experiments log after run
        - logs_dir (str): directory to auto_save logs
        - telegram_token (str): optional bot token for telegram
    '''

    def __init__(self, auto_save_logs=False, logs_dir='exp_runs', telegram_token=None):
        self.file_buffers = {}
        self.logs = {}
        self.auto_save_logs = auto_save_logs
        self.logs_dir = logs_dir
        self.telegram_token = telegram_token

        if auto_save_logs:
            with suppress(FileExistsError):
                os.mkdir(logs_dir)

    @contextlib.contextmanager
    def redirect_file_output(self, fname=None, mode='r', *args, **kwargs):
        '''
        Dropin replacement for open that automatically
        redirects files open in 'w' mode to a StringIO dict

        args:
            default arguments for open
        '''

        if mode == 'w':
            # create a stringio for each file
            if fname not in self.file_buffers:
                self.file_buffers[fname] = StringIO()
            fh = self.file_buffers[fname]
        else:
            fh = builtins.open(fname, mode, *args, **kwargs)

        try:
            yield fh
        finally:
            if mode != 'w':
                fh.close()

    def log(self, name, collect_print=False, collect_files=False):
        '''
        Decorator to log a given experiment, i.e., function collecting data about it

        args:
            - name (str): how to call the function
            - collect_prints (boolean): collect all prints inside the function
            - collect_files (boolean): collect all strings written to files (in 'w' mode)
                **** This may result in unexpected behaviours
                if the function writes something to files other than log data ****
        '''

        def wrapper(func):
            @wraps(func)
            def nested_f(*args, **kwargs):
                if collect_files:
                    # change open function behaviour to write to stringio
                    func.__globals__.update({'open': self.redirect_file_output})

                start_time = datetime.datetime.now()
                # redirects function sys.stdout to stringio
                if collect_print:
                    sio = StringIO()
                    # redirect stdout to stringio
                    with redirect_stdout(sio):
                        return_values = func(*args, **kwargs)
                    print_data = sio.getvalue().splitlines()
                else:
                    return_values = func(*args, **kwargs)
                    print_data = None

                end_time = datetime.datetime.now()

                if collect_files:
                    # restore default behaviour
                    func.__globals__.update({'open': builtins.open})
                    # parse text written to log files inside function
                    files_data = {fname: [s.strip() for s in b.getvalue().splitlines()]
                                  for fname, b in self.file_buffers.items()}
                else:
                    files_data = None

                json_data = {'start time': str(start_time),
                             'end time': str(end_time),
                             'elapsed time': str(end_time - start_time),
                             'input values': 'args: {} kwargs: {}'.format(args, kwargs),
                             'prints': print_data,
                             'log files outputs': files_data,
                             'return values': str(return_values)
                            }

                execution_name = '{} ({})'.format(name, start_time)
                if self.auto_save_logs:
                    fname = os.path.join(self.logs_dir, execution_name + '.json')
                    with open(fname, 'w') as file:
                        json.dump(json_data, file)
                self.logs[execution_name] = json_data

                return return_values

            return nested_f

        return wrapper


    def notify_via_telegram(self, name, chat_id):
        '''
        Decorator to send a message to a telegram user/group when a experiment finishes

        args:
            - name (str): how to call the function
            - chat_id (str): ID of group or user
        '''

        def wrapper(func):
            @wraps(func)
            def nested_f(*args, **kwargs):
                try:
                    bot = telegram.Bot(token=self.telegram_token)
                except telegram.error.InvalidToken:
                    msg = 'Unable to create a telegram bot. Check if token exists.'
                    raise TelegramException(msg)

                start_time = datetime.datetime.now()

                return_values = func(*args, **kwargs)

                end_time = datetime.datetime.now()

                elapsed_time = end_time - start_time

                str_args = name, end_time, elapsed_time
                text = '{} finished running at {} (elapsed time {})'.format(*str_args)

                # check if something happend and raise a wanring
                # not raising error to allow for the experiment to finish
                try:
                    bot.sendMessage(chat_id=chat_id, text=text)
                except telegram.error.BadRequest:
                    msg = 'Unable to find chat with id {}.'.format(chat_id)
                    warnings.warn(msg, UserWarning)
                except telegram.error.Unauthorized:
                    msg = 'Unauthorized access (may be related to token).'
                    warnings.warn(msg, UserWarning)

                return return_values

            return nested_f

        return wrapper
