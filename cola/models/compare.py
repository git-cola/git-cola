from cola.models.main import MainModel

class CompareModel(MainModel):
    """Provides custom model data for CompareController."""
    def __init__(self):
        MainModel.__init__(self)
        self.descriptions_start = []
        self.descriptions_end = []
        self.revisions_start = []
        self.revisions_end = []
        self.revision_start = ''
        self.revision_end = ''
        self.compare_files = []
        self.num_results = 100
        self.show_versions=False

class BranchCompareModel(MainModel):
    """Provides custom model data for BranchCompareController."""
    def __init__(self):
        MainModel.__init__(self)
        self.left_combo = ['Local', 'Remote']
        self.right_combo = ['Local', 'Remote']
        self.left_combo_index = 0
        self.right_combo_index = 1
        self.left_list = []
        self.right_list = []
        self.left_list_index = -1
        self.right_list_index = -1
        self.left_list_selected = False
        self.right_list_selected = False
        self.diff_files = []
