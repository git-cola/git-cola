#!/usr/bin/env python
# Author: David Aguilar

"""
pyuic4: support for generating .py Python scripts from Qt Designer4 .ui files.

NOTES:

- If PYQT4_ROOT is given(absolute path), the configuration will look
  in PYQT4_ROOT/bin first.

- This module hooks adds a python hook that runs
  a pyuic4 action when '.ui' files are encoutnered.


"""
import os

import Action
import Object
import Params

import python
python.pyobj.s_default_ext.append('.ui')

def set_options(opt):
    """Adds the --pyuic4 build option."""
    opt.add_option('--pyuic4',
                   type='string',
                   dest='pyuic4',
                   default='',
                   help='path to pyuic4')

def create_pyuic4_tasks(self, node):
    """Creates the tasks to generate python files.
    The "pyuic4" action is called for this."""

    # Create a pyuic4 task to generate the python .py file
    pyuic4task = self.create_task('pyuic4')
    pyuic4task.set_inputs(node)
    pyuic4task.set_outputs(node.change_ext('.py'))

    # Add the python compilation tasks
    if self.pyc:
        task = self.create_task('pyc', self.env, 50)
        task.set_inputs(node.change_ext('.py'))
        task.set_outputs(node.change_ext('.pyc'))

    if self.pyo:
        task = self.create_task('pyo', self.env, 50)
        task.set_inputs(node.change_ext('.py'))
        task.set_outputs(node.change_ext('.pyo'))

def setup(env):
    """Creates a python hook and registers it with the environment."""
    # create the hook action
    cmd_template = '${PYUIC4} ${PYUIC4_FLAGS} ${SRC} -o ${TGT}'
    Action.simple_action('pyuic4', cmd_template, 'GREEN')

    # register .ui for use with python
    Object.hook('py', 'PYUIC4_EXT', create_pyuic4_tasks)

def detect(conf):
    env = conf.env
    opt = Params.g_options

    pyuic4 = None
    try:
        pyuic4 = opt.pyuic4
    except:
        pass

    if not pyuic4:
        qtdir = os.environ.get('PYQT4_ROOT', '')
        if qtdir:
            binpath = [qtdir] + os.environ['PATH'].split(':')
        else:
            binpath = os.environ['PATH'].split(':')

        for f in ['pyuic4', 'pyuic-qt4', 'pyuic']:
            pyuic4 = conf.find_program(f, path_list=binpath)
            if pyuic4:
                break

    if not pyuic4:
        conf.check_message('pyuic4 binary', '(not found)', 0)
        Params.fatal('Error: missing PyQt4 development tools.')
        return False

    # Set the path to pyuic4
    env['PYUIC4'] = pyuic4
    env['PYUIC4_EXT'] = ['.ui']
    env['PYUIC4_FLAGS'] = '-x'

    vercmd = env['PYUIC4'] + ' --version 2>&1'
    version = os.popen(vercmd).read().strip().split(' ')[-1]
    version = version.split('.')[0]
    if not version.isdigit() or int(version) < 4:
        conf.check_message('pyuic4 version', '(not found or too old)', 0,
                option= '(%s)' % version)
        return False

    conf.check_message('pyuic4 version', '', 1, option='(%s)' % version)

    # all tests passed
    return True
