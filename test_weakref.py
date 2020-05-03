"""
weakref should be valid.
"""

import gc

import importlib

import autoreload
import retroreload


switch = 2

if switch == 0:
    reload_module = importlib.reload
elif switch == 1:
    reload_module = autoreload.superreload
elif switch == 2:
    reload_module = retroreload.retroreload


import mod3


if __name__ == '__main__':
    dispatcher = mod3.Dispatcher()
    c = mod3.C()
    dispatcher.register(c.func)
    dispatcher.dispatch()

    input('modify mod3.py if you like, and press enter')
    reload_module(mod3)

    print('gc before')
    gc.collect()
    print('gc after')

    dispatcher.dispatch()

    # builtin: preserve weakref, but result is bad
    # autoreload: loses weakref when gc.collect is called, cb() returns None
    # retroreload: preserve weakref, result is good
