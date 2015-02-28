#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for qtpy
"""
from setuptools import setup, find_packages


def read_version():
    with open("qtpy/__init__.py") as f:
        lines = f.read().splitlines()
        for l in lines:
            if "__version__" in l:
                return l.split("=")[1].strip().replace("'", '').replace('"', '')


def readme():
    return str(open('README.md').read())


setup(
    name='pyqode.qt',
    version=read_version(),
    packages=[p for p in find_packages() if 'test' not in p],
    keywords=["qt PyQt4 PyQt5 PySide"],
    url='https://github.com/goanpeca/qtpy',
    license='MIT',
    author='Gonzalo Peña-Castellanos',
    author_email='goanpeca@gmail.com',
    description='Provides an abstraction layer on top of the various Qt '
                'bindings (PyQt5, PyQt4 and PySide)',
    long_description=readme(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: Qt',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Widget Sets'])
