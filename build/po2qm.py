#!/usr/bin/env python
import os
import Action
import Object
import Params
import Utils
import Common

"Converts .po files to the Qt .qm format"

NAME='po2qm'
class po2qm_obj(Object.genobj):

	s_default_ext = ['.po']
	def __init__(self):
		Object.genobj.__init__(self, 'other')
		self.inst_var = 'QMDIR'
		self.inst_dir = ''
		self.chmod = 0644
	
	def apply(self):
		# create the nodes corresponding to the sources
		for filename in self.to_list(self.source):

			base, ext = os.path.splitext(filename)
			if not ext in self.s_default_ext:
				Params.fatal("unknown file " + filename)

			split_filename = Utils.split_path(filename)
			node = self.path.find_source_lst(split_filename)

			task = self.create_task(NAME, self.env, 101)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.qm'))
	
	def install(self):
		for i in self.m_tasks:
			current = Params.g_build.m_curdirnode
			lst=[a.relpath_gen(current) for a in i.m_outputs]
			Common.install_files(self.inst_var, self.inst_dir, lst, chmod=self.chmod)

def setup(env):
	Object.register(NAME, po2qm_obj)
	Action.simple_action(NAME, '${MSGFMT} ${MSGFMT_FLAGS} -o ${TGT} ${SRC}', color='YELLOW')

def detect(conf):
	if not conf.find_program('msgfmt', var='MSGFMT'):
		Params.fatal('Error: missing msgfmt executable.')
		return False
	conf.env['MSGFMT_FLAGS'] = '--qt'
	conf.env['MSGFMT_EXT'] = ['.po']
	conf.env['QMDIR'] = os.path.join(
				conf.env['PREFIX'], 'share',
				Utils.g_module.APPNAME, 'qm')
	return True
