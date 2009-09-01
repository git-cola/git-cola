from cola.models import main

class SearchModel(main.MainModel):
    def __init__(self, cwd=None):
        main.MainModel.__init__(self, cwd=cwd)
        self.query = ''
        self.max_results = 500
        self.start_date = ''
        self.end_date = ''
        self.commit_list = []
