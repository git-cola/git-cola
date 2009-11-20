import helper
import os

from cola.models import main

class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.models.main.MainModel class."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self, commit=True)
        self.model = main.MainModel(cwd=os.getcwd())
        self.model.use_worktree(os.getcwd())

    def test_project(self):
        """Test the MainModel's 'project' attribute."""
        project = os.path.basename(self.get_dir())
        self.assertEqual(self.model.project, project)

    def test_local_branches(self):
        self.model.update_status()
        self.assertEqual(self.model.local_branches, ['master'])
