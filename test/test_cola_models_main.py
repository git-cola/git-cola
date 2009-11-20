import helper
import os

from cola.models import main

class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.models.main.MainModel class."""

    def setup_baseline_repo(self, commit=True):
        """Create a baseline repo for testing."""
        self.shell("""
            git init >/dev/null &&
            touch the-file &&
            git add the-file
        """)
        if commit:
            self.shell("git commit -s -m'Initial commit' >/dev/null")

    def test_project(self):
        """Test the MainModel's 'project' attribute."""
        self.setup_baseline_repo()
        model = main.MainModel()
        model.use_worktree(os.getcwd())
        project = os.path.basename(self.get_dir())
        self.assertEqual(project, model.project)
