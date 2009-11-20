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

    def test_remote_branches(self):
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, [])

        self.shell("""
                git remote add origin .
                git fetch origin > /dev/null 2>&1
        """)
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, ['origin/master'])

    def test_modified(self):
        self.shell('echo change > A')
        self.model.update_status()
        self.assertEqual(self.model.modified, ['A'])
