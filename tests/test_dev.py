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

    def test_install_command_is_npm_install(self):
        cmd, cwd = dev.install_command(Path("/proj"))
        self.assertEqual(cwd, Path("/proj") / "portal-admin-frontend")
        self.assertEqual(cmd[:3], [shutil.which("npm") or "npm", "install"])


class EnsureFrontendDepsTests(unittest.TestCase):
    def test_skips_when_node_modules_present(self):
        root = Path("/proj")
        with patch.object(dev, "FRONTEND_DIR", root / "portal-admin-frontend"), \
             patch.object(Path, "exists", lambda self: self.name == "node_modules" or str(self).endswith("node_modules")), \
             patch.object(dev, "run_blocking") as run:
            self.assertTrue(dev.ensure_frontend_deps(root))
        run.assert_not_called()

    def test_runs_npm_install_when_node_modules_missing(self):
        root = Path("/proj")
        fe = root / "portal-admin-frontend"

        def fake_exists(self):
            # only node_modules path is missing
            return not str(self).endswith("node_modules")

        with patch.object(Path, "exists", fake_exists), \
             patch.object(dev, "run_blocking", return_value=0) as run:
            self.assertTrue(dev.ensure_frontend_deps(root))
        run.assert_called_once()
        cmd, cwd = run.call_args[0][0], run.call_args[0][1]
        self.assertEqual(cwd, fe)
        self.assertIn("install", cmd)

    def test_returns_false_when_npm_install_fails(self):
        root = Path("/proj")

        def fake_exists(self):
            return not str(self).endswith("node_modules")

        with patch.object(Path, "exists", fake_exists), \
             patch.object(dev, "run_blocking", return_value=1):
            self.assertFalse(dev.ensure_frontend_deps(root))


class WaitUntilListeningTests(unittest.TestCase):
    def test_returns_true_when_port_open(self):
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)
        try:
            self.assertTrue(dev.wait_until_listening("127.0.0.1", port, timeout=2))
        finally:
            srv.close()

    def test_returns_false_when_port_closed(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()  # free it, nothing listening
        self.assertFalse(dev.wait_until_listening("127.0.0.1", port, timeout=0.5))


if __name__ == "__main__":
    unittest.main()
