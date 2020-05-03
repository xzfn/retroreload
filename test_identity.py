
"""
identity test.
id should not change after reloading.
NOTE: for buildin reload, id may not change, but the basic result is wrong.
"""

import importlib

import autoreload
import retroreload

import mod

switch = 2

if switch == 0:
    reload_module = importlib.reload
elif switch == 1:
    reload_module = autoreload.superreload
elif switch == 2:
    reload_module = retroreload.retroreload

if __name__ == '__main__':
    c = mod.C()

    before_class_id = id(mod.C)
    before_func_id = id(mod.func)
    before_method_id = id(mod.C.method)
    before_bound_method_id = id(c.method)
    before_object_class_id = id(c.__class__)

    reload_module(mod)

    after_class_id = id(mod.C)
    after_func_id = id(mod.func)
    after_method_id = id(mod.C.method)
    after_bound_method_id = id(c.method)
    after_object_class_id = id(c.__class__)

    # function id should not change
    # result: builtin bad, superreload bad, retroreload good
    print('function id', 'before', before_func_id, 'after', after_func_id)

    # class id should not change
    # result: builtin bad, superreload bad, retroreload good
    print('class id', 'before', before_class_id, 'after', after_class_id)

    # method id should not change
    # result: builtin bad, superreload bad, retroreload good
    print('method id', 'before', before_method_id, 'after', after_method_id)

    # bound method id should not change
    # result: builtin good, superreload good, retroreload good
    print('bound method id', 'before', before_bound_method_id, 'after', after_bound_method_id)

    # object __class__ id should not change
    # result: buildin good, superreload bad, retroreload good
    print('object class id', 'before', before_object_class_id, 'after', after_object_class_id)
