from commands import getoutput
from model import Model
def get_config(key):
	return getoutput('git config --get "%s"' % key)
class GitModel(Model):
	def __init__(self): Model.__init__(self, {
				'commitmsg':	'',
				'staged':	[],
				'unstaged':	[],
				'name':		get_config('user.name'),
				'email':	get_config('user.email'),
				})


