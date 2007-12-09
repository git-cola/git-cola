#!/usr/bin/env python
# encoding: utf-8
# David Aguilar

"""
pyuic4: support for generating .py Python scripts from Qt Designer .ui files.

NOTES:

- If PYQT4_ROOT is given (absolute path), the configuration will look
  in PYQT4_ROOT/bin first.

- This module hooks adds a python hook that runs
  a pyuic4 action when '.ui' files are encoutnered.


"""
import os

import Action
import Params

import python
python.pyobj.s_default_ext.append('.ui')


def create_pyuic4_tasks(self, node):

	'''Creates the tasks to generate python files.
	The 'pyuic4' action is called for this.'''

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
	# create the hook action
        cmd_template = '${PYUIC4} ${PYUIC4_FLAGS} ${SRC} -o ${TGT}'
        cmd_color = 'BLUE'
	Action.simple_action( 'pyuic4', cmd_template, cmd_color )

	# register .ui for use with python
	env.hook('py', 'PYUIC4_EXT', create_pyuic4_tasks)


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
		return False

	# Set the path to pyuic4
	env['PYUIC4'] = pyuic4
	env['PYUIC4_EXT'] = ['.ui']
	env['PYUIC4_FLAGS'] = '-x'

	version = os.popen(env['PYUIC4'] + ' --version 2>&1').read().strip().split(' ')[-1]
	version = version.split('.')[0]
	if int(version) < 4:
		conf.check_message('pyuic version', '(too old)', 0, option= '(%s)' % version)
		return False

	conf.check_message('pyuic4 version', '', 1, option='(%s)' % version)

	# all tests passed
	return True


def set_options(opt):
	opt.add_option( '--pyuic4',
		type='string', dest='pyuic4', default='',
		help='path to the pyuic4 binary')

