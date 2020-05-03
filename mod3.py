
import weakref

class Dispatcher(object):
    def __init__(self):
        self.callbacks = []

    def register(self, f):
        self.callbacks.append(weakref.WeakMethod(f, lambda a: print('claimed', a)))

    def dispatch(self):
        for cb in self.callbacks:
            cb()()

class C(object):
    def func(self):
        print('ouch')
        # print('ouch2')
