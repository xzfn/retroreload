# retroreload
Python real reload stripped from ipython autoreload extension.


Does not change identity after reloading, which should be a good thing.

Does not update module variables, which may or may not be a good thing.

Mental comparison with builtin reload and ipython autoreload:
* builtin reload: get new, use new and discard old.
* autoreload: get new, update old using new, use both updated old and new.
* retroreload: get new, update old using new, use updated old and discard new.
