import commands
from model import Model

def get_config(key):
	return commands.getoutput('git config --get "%s"' % key)

class GitModel(Model):
	def __init__ (self): Model.__init__(self, {
				'commitmsg':	'',
				'staged':	[],
				'unstaged':	[],
				'untracked':	[],
				'name':		get_config('user.name'),
				'email':	get_config('user.email'),
				})
