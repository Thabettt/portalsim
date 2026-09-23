import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import dev


class FindBackendPythonTests(unittest.TestCase):
    def test_resolves_windows_venv_layout(self):
        root = Path("C:/proj")
        venv_py = root / ".venv" / "Scripts" / "python.exe"
        with patch.object(Path, "exists", lambda self: self == venv_py):
            self.assertEqual(dev.find_backend_python(root), venv_py)

    def test_resolves_posix_venv_layout(self):
        root = Path("/proj")
        venv_py = root / ".venv" / "bin" / "python"
        with patch.object(Path, "exists", lambda self: self == venv_py):
            self.assertEqual(dev.find_backend_python(root), venv_py)

    def test_falls_back_to_current_interpreter_without_venv(self):
        root = Path("/proj")
        with patch.object(Path, "exists", lambda self: False):
            self.assertEqual(dev.find_backend_python(root), Path(sys.executable))


class CommandBuilderTests(unittest.TestCase):
    def test_backend_command_forces_port_and_host(self):
        py = Path("/proj/.venv/bin/python")
        cmd, cwd = dev.backend_command(py, Path("/proj"))
        self.assertEqual(cwd, Path("/proj"))
        self.assertEqual(cmd[0], str(py))
        self.assertIn("--port", cmd)
        self.assertIn("6767", cmd)
        self.assertIn("--host", cmd)
        self.assertIn("0.0.0.0", cmd)
        self.assertIn("app.main:app", cmd)
        self.assertIn("--reload", cmd)
        self.assertIn("--reload-dir", cmd)
        i = cmd.index("--reload-dir")
        self.assertEqual(cmd[i + 1], "app")

    def test_frontend_command_runs_npm_dev_with_host(self):
        cmd, cwd = dev.frontend_command(Path("/proj"))
        self.assertEqual(cwd, Path("/proj") / "portal-admin-frontend")
        self.assertEqual(cmd[1:3], ["run", "dev"])
        self.assertIn("--host", cmd)

    def test_frontend_command_embeds_resolved_npm_path(self):
        cmd, _ = dev.frontend_command(Path("/proj"))
        self.assertIsNotNone(shutil.which("npm"), "npm must be on PATH")
        self.assertEqual(cmd[0], shutil.which("npm"))


if __name__ == "__main__":
    unittest.main()
