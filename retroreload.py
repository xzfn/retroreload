"""
Real reload.

Stripped from ipython IPython/extensions/autoreload.py

autoreload:
  get new, update old using new, use both updated old and new.
retroreload:
  get new, update old using new, use updated old and discard new.
"""


#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
import sys
import traceback
import types
import weakref
import gc
from importlib import import_module
from importlib.util import source_from_cache
from importlib import reload

#------------------------------------------------------------------------------
# Autoreload functionality
#------------------------------------------------------------------------------

class ModuleReloader(object):
    enabled = False
    """Whether this reloader is enabled"""

    check_all = True
    """Autoreload all modules, not just those listed in 'modules'"""

    def __init__(self):
        # Modules that failed to reload: {module: mtime-on-failed-reload, ...}
        self.failed = {}
        # Modules specially marked as autoreloadable.
        self.modules = {}
        # Modules specially marked as not autoreloadable.
        self.skip_modules = {}
        # (module-name, name) -> weakref, for replacing old code objects
        self.old_objects = {}
        # Module modification timestamps
        self.modules_mtimes = {}

        # Cache module modification times
        self.check(check_all=True, do_reload=False)

    def mark_module_skipped(self, module_name):
        """Skip reloading the named module in the future"""
        try:
            del self.modules[module_name]
        except KeyError:
            pass
        self.skip_modules[module_name] = True

    def mark_module_reloadable(self, module_name):
        """Reload the named module in the future (if it is imported)"""
        try:
            del self.skip_modules[module_name]
        except KeyError:
            pass
        self.modules[module_name] = True

    def aimport_module(self, module_name):
        """Import a module, and mark it reloadable
        Returns
        -------
        top_module : module
            The imported module if it is top-level, or the top-level
        top_name : module
            Name of top_module
        """
        self.mark_module_reloadable(module_name)

        import_module(module_name)
        top_name = module_name.split('.')[0]
        top_module = sys.modules[top_name]
        return top_module, top_name

    def filename_and_mtime(self, module):
        if not hasattr(module, '__file__') or module.__file__ is None:
            return None, None

        if getattr(module, '__name__', None) in [None, '__mp_main__', '__main__']:
            # we cannot reload(__main__) or reload(__mp_main__)
            return None, None

        filename = module.__file__
        path, ext = os.path.splitext(filename)

        if ext.lower() == '.py':
            py_filename = filename
        else:
            try:
                py_filename = source_from_cache(filename)
            except ValueError:
                return None, None

        try:
            pymtime = os.stat(py_filename).st_mtime
        except OSError:
            return None, None

        return py_filename, pymtime

    def check(self, check_all=False, do_reload=True):
        """Check whether some modules need to be reloaded."""

        if not self.enabled and not check_all:
            return

        if check_all or self.check_all:
            modules = list(sys.modules.keys())
        else:
            modules = list(self.modules.keys())

        for modname in modules:
            m = sys.modules.get(modname, None)

            if modname in self.skip_modules:
                continue

            py_filename, pymtime = self.filename_and_mtime(m)
            if py_filename is None:
                continue

            try:
                if pymtime <= self.modules_mtimes[modname]:
                    continue
            except KeyError:
                self.modules_mtimes[modname] = pymtime
                continue
            else:
                if self.failed.get(py_filename, None) == pymtime:
                    continue

            self.modules_mtimes[modname] = pymtime

            # If we've reached this point, we should try to reload the module
            if do_reload:
                try:
                    superreload(m, reload, self.old_objects)
                    if py_filename in self.failed:
                        del self.failed[py_filename]
                except:
                    print("[autoreload of %s failed: %s]" % (
                            modname, traceback.format_exc(10)), file=sys.stderr)
                    self.failed[py_filename] = pymtime

#------------------------------------------------------------------------------
# superreload
#------------------------------------------------------------------------------


func_attrs = ['__code__', '__defaults__', '__doc__',
              '__closure__', '__globals__', '__dict__']


def update_function(old, new):
    """Upgrade the code object of a function"""
    for name in func_attrs:
        try:
            setattr(old, name, getattr(new, name))
        except (AttributeError, TypeError):
            pass


def update_instances(old, new):
    """Use garbage collector to find all instances that refer to the old
    class definition and update their __class__ to point to the new class
    definition"""
    
    refs = gc.get_referrers(old)

    for ref in refs:
        if type(ref) is old:
            ref.__class__ = new


def update_class(old, new):
    """Replace stuff in the __dict__ of a class, and upgrade
    method code objects, and add new methods, if any"""
    for key in list(old.__dict__.keys()):
        old_obj = getattr(old, key)
        try:
            new_obj = getattr(new, key)
            # explicitly checking that comparison returns True to handle
            # cases where `==` doesn't return a boolean.
            if (old_obj == new_obj) is True:
                continue
        except AttributeError:
            # obsolete attribute: remove it
            try:
                delattr(old, key)
            except (AttributeError, TypeError):
                pass
            continue

        if update_generic(old_obj, new_obj): continue

        try:
            setattr(old, key, getattr(new, key))
        except (AttributeError, TypeError):
            pass # skip non-writable attributes

    for key in list(new.__dict__.keys()):
        if key not in list(old.__dict__.keys()):
            try:
                setattr(old, key, getattr(new, key))
            except (AttributeError, TypeError):
                pass # skip non-writable attributes

    # retroreload: do not update old __class__
    # update all instances of class
    # update_instances(old, new)


def update_property(old, new):
    """Replace get/set/del functions of a property"""
    update_generic(old.fdel, new.fdel)
    update_generic(old.fget, new.fget)
    update_generic(old.fset, new.fset)


def isinstance2(a, b, typ):
    return isinstance(a, typ) and isinstance(b, typ)


UPDATE_RULES = [
    (lambda a, b: isinstance2(a, b, type),
     update_class),
    (lambda a, b: isinstance2(a, b, types.FunctionType),
     update_function),
    (lambda a, b: isinstance2(a, b, property),
     update_property),
]
UPDATE_RULES.extend([(lambda a, b: isinstance2(a, b, types.MethodType),
                      lambda a, b: update_function(a.__func__, b.__func__)),
])


def update_generic(a, b):
    for type_check, update in UPDATE_RULES:
        if type_check(a, b):
            update(a, b)
            return True
    return False


class StrongRef(object):
    def __init__(self, obj):
        self.obj = obj
    def __call__(self):
        return self.obj


def superreload(module, reload=reload, old_objects=None):
    """Enhanced version of the builtin reload function.
    superreload remembers objects previously in the module, and
    - upgrades the class dictionary of every old class in the module
    - upgrades the code object of every old function and method
    - clears the module's namespace before reloading
    """
    if old_objects is None:
        old_objects = {}

    # collect old objects in the module
    for name, obj in list(module.__dict__.items()):
        if not hasattr(obj, '__module__') or obj.__module__ != module.__name__:
            continue
        key = (module.__name__, name)
        try:
            # retroreload: use strong ref
            old_objects.setdefault(key, []).append(StrongRef(obj))
        except TypeError:
            pass

    # reload module
    try:
        # clear namespace first from old cruft
        old_dict = module.__dict__.copy()
        old_name = module.__name__
        module.__dict__.clear()
        module.__dict__['__name__'] = old_name
        module.__dict__['__loader__'] = old_dict['__loader__']
    except (TypeError, AttributeError, KeyError):
        pass

    try:
        module = reload(module)
    except:
        # restore module dictionary on failed reload
        module.__dict__.update(old_dict)
        raise

    # iterate over all objects and update functions & classes
    for name, new_obj in list(module.__dict__.items()):
        key = (module.__name__, name)
        if key not in old_objects: continue

        new_refs = []
        for old_ref in old_objects[key]:
            old_obj = old_ref()
            if old_obj is None: continue
            new_refs.append(old_ref)
            update_generic(old_obj, new_obj)

        if new_refs:
            old_objects[key] = new_refs
        else:
            del old_objects[key]

    # retroreload: use updated old, discard new
    module.__dict__.update(old_dict)
    return module



#------------------------------------------------------------------------------
# retroreload
#------------------------------------------------------------------------------

import time


DRY_RUN = False

LAST_RELOAD_TIMES = {}

START_TIME = time.time()


def retroreload(module):
    print('retroreload module: ', module)
    if not DRY_RUN:
        superreload(module)

def retroreload_module_name(module_name):
    module = sys.modules.get(module_name)
    if module:
        if is_module_outdated(module, module_name):
            retroreload(module)
            LAST_RELOAD_TIMES[module_name] = time.time()

def retroreload_module_names(module_names):
    for module_name in module_names:
        retroreload_module_name(module_name)

def absnormpath(path):
    return os.path.normpath(os.path.abspath(path))

def retroreload_script_folder(script_folder):
    script_folder = absnormpath(script_folder)
    reload_module_names = []
    for module_name, module in sys.modules.items():
        module_file = getattr(module, '__file__', '')
        if module_file:
            module_file = absnormpath(module_file)
            if module_file.startswith(script_folder):
                reload_module_names.append(module_name)
    retroreload_module_names(reload_module_names)

def retroreload_script_folders(script_folders):
    for script_folder in script_folders:
        retroreload_script_folder(script_folder)

def is_module_outdated(module, module_name):
    """
    The module should be reloaded only if outdated.
    
    module file modified time is later than START_TIME and 
    _retroreload_last_reload_time(if exists)
    """
    module_file = getattr(module, '__file__', '')
    if not module_file:
        return False
    modified_time = os.path.getmtime(module_file)
    if module_name in LAST_RELOAD_TIMES:
        last_reload_time = LAST_RELOAD_TIMES[module_name]
        if modified_time > last_reload_time:
            return True
        return False
    else:
        if modified_time > START_TIME:
            return True
        return False
