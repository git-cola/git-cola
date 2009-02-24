# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self.__observers = []
        self.__notify = True
    def get_observers(self):
        return self.__observers
    def set_observers(self, observers):
        self.__observers = observers
    def get_notify(self):
        return self.__notify
    def set_notify(self, notify=True):
        self.__notify = notify
    def add_observer(self, observer):
        if observer not in self.__observers:
            self.__observers.append(observer)
    def remove_observer(self, observer):
        if observer in self.__observers:
            self.__observers.remove(observer)
    def notify_observers(self, *param):
        if not self.__notify:
            return
        for observer in self.__observers:
            observer.notify(*param)
