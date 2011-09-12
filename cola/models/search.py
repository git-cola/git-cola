from cola.main.model import MainModel

class SearchModel(MainModel):
    def __init__(self, cwd=None):
        MainModel.__init__(self, cwd=cwd)
        self.query = ''
        self.max_results = 500
        self.start_date = ''
        self.end_date = ''
        self.commit_list = []
