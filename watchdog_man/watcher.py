import builtins
import contextlib
import datetime
import json
import os
import pickle
import sys
import types
import warnings
from collections import defaultdict
from contextlib import redirect_stdout, suppress
from functools import wraps
from io import StringIO

with suppress(ImportError):
    import telegram


class TelegramException(ValueError):
    pass

class Vault:
    def __init__(self):
        self.stored_objects = {}

    def __repr__(self):
        arg = ','.join(self.stored_objects.keys())
        return 'Vault with objects ({})'.format(arg)

    def __setattr__(self, name, value):
        if name != 'stored_objects':
            self.stored_objects[name] = value
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        '''
        intercept lookups which would raise an exception
        to check if variable is being stored
        '''

        if name in self.stored_objects:
            return self.stored_objects[name]
        else:
            return super().__getattr__(name)

    def pickle_safe(self, file):
        pickle.dump(self, open(file, 'wb'))

class Watcher:
    '''
    Base class for watchdog_man. A single watcher is capable of loging multiple functions.

    args:
        - handle_multiple_calls (boolean): automatically handles multiple calls of
            the same function by appending a number at the end of the function id

        - auto_save_logs (boolean): automatically save experiments log after run

        - logs_dir (str): directory to auto_save logs

        - telegram_token (str): optional bot token for telegram
    '''

    def __init__(self, handle_multiple_calls=False,
                 auto_save_logs=False,
                 logs_dir='exp_runs',
                 telegram_token=None):

        self.file_buffers = {}
        self.logs = {}
        self.vaults = {}

        self.handle_multiple_calls = handle_multiple_calls
        if handle_multiple_calls:
            self.call_counter_log = defaultdict(int)
            self.call_counter_vault = defaultdict(int)

        self.auto_save_logs = auto_save_logs
        self.logs_dir = logs_dir
        self.telegram_token = telegram_token

        if auto_save_logs:
            with suppress(FileExistsError):
                os.mkdir(logs_dir)

    @contextlib.contextmanager
    def redirect_file_output(self, fname=None, mode='r', *args, **kwargs):
        '''
        Drop-in replacement for open that automatically
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

    def log(self, function_name, collect_print=False, collect_files=False):
        '''
        Decorator to log a given experiment, i.e., function collecting data about it

        args:
            - function_name (str): name of the function
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

                if self.handle_multiple_calls:
                    n = self.call_counter_log[function_name]
                    self.call_counter_log[function_name] += 1
                    function_id = '{}_{}'.format(function_name, n)
                else:
                    function_id = function_name

                if self.auto_save_logs:
                    fname = os.path.join(self.logs_dir, function_id + '.json')
                    with open(fname, 'w') as file:
                        json.dump(json_data, file)
                self.logs[function_id] = json_data

                return return_values
            return nested_f
        return wrapper

    def notify_via_telegram(self, function_name, chat_id):
        '''
        Decorator to send a message to a telegram user/group when a experiment finishes

        args:
            - function_name (str): name of the function
            - chat_id (str): ID of group or user
        '''

        def wrapper(func):
            if 'telegram' not in sys.modules:
                raise Exception('To use this feature you must '
                                'have python-telegram-bot installed')

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

                str_args = function_name, end_time, elapsed_time
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

    def object_vault(self, function_name):
        '''
        Decorator to provide a vault to store multiple objects.

        args:
        - function_name (str): name of the function
        - chat_id (str): ID of group or user

        **** Note that the function being decorated must have
        as its first argument the vault. All variables
        must be stored to this vault ****

        '''
        def wrapper(func):
            @wraps(func)
            def nested_f(*args, **kwargs):
                vault = Vault()
                return_values = func(vault, *args, **kwargs)

                if self.handle_multiple_calls:
                    n = self.call_counter_vault[function_name]
                    self.call_counter_vault[function_name] += 1
                    function_id = '{}_{}'.format(function_name, n)
                else:
                    function_id = function_name

                self.vaults[function_id] = vault

                return return_values
            return nested_f
        return wrapper

    # TODO
    # def follow_variables(self, *names):
    #     def wrapper(func):
    #         @wraps(func)
    #         def nested_f(*args, **kwargs):
    #             return_values = func(*args, **kwargs)
    #             return return_values
    #         return nested_f
    #     return wrapper
