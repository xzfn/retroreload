"""
basic result test.
the results should update after reloading.
NOTE: retroreload does not update module variables.
"""

import time
import shutil

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


def use_before():
    shutil.copy2('mod2_before.py', 'mod2.py')
    time.sleep(0.2)


def use_after():
    shutil.copy2('mod2_after.py', 'mod2.py')
    time.sleep(0.2)


if __name__ == '__main__':
    use_before()
    import mod2
    print('------------------', 'before', '------------------')

    print('function', mod2.func() == 'before')
    func = mod2.func
    print('function2', func() == 'before')
    c = mod2.C()
    print('method', c.meth() == 'before')
    meth = c.meth
    print('bound method', meth() == 'before')

    print('const', mod2.CONST == 'before')
    const = mod2.CONST
    print('const2', const == 'before')

    use_after()

    reload_module(mod2)

    print('------------------', 'after', '------------------')
    print('function', mod2.func() == 'after')
    print('function2', func() == 'after')
    print('method', c.meth() == 'after')
    print('bound method', meth() == 'after')

    print('const', mod2.CONST == 'after')
    print('const2', const == 'after')

    # ---functions and methods---:
    # builtin: True False False False
    # autoreload: True True True True
    # retroreload: True True True True

    # ---consts---:
    # builtin: True False
    # autoreload: True False
    # retroreload: False False  # intented, does not update module variable
