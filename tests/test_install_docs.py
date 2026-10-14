"""Run the documented PowerShell installation in an isolated destination."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")


@unittest.skipUnless(PWSH, "PowerShell 7 is not available")
class DocumentedInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="website-trust-install-test-")
        self.destination = Path(self.temp.name) / "installed-skill"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"```powershell\s*\n(.*?)\n```", readme, re.S)
        self.assertIsNotNone(match, "README needs an executable PowerShell installation block")
        self.command = match.group(1)
        # Replace only the destination line; do not change CODEX_HOME or user settings.
        target = str(self.destination).replace("'", "''")
        self.command, count = re.subn(r"(?m)^\$target\s*=.*$", lambda _: f"$target = '{target}'", self.command)
        self.assertEqual(1, count)

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", self.command],
                              cwd=ROOT, capture_output=True, encoding="utf-8")

    def test_copy_matches_source_and_excludes_runtime_files(self):
        result = self.install()
        self.assertEqual(0, result.returncode, result.stderr)
        for relative in ("SKILL.md", "scripts/validate_audit.py", "references/baseline.md", "assets/example-audit.json"):
            self.assertEqual((ROOT / relative).read_bytes(), (self.destination / relative).read_bytes())
        excluded = {".git", "__pycache__", "evidence", "runs"}
        for item in self.destination.rglob("*"):
            self.assertFalse(excluded.intersection(item.relative_to(self.destination).parts))
            self.assertNotEqual(".pyc", item.suffix)

    def test_existing_install_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("existing colleague work", encoding="utf-8")
        result = self.install()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("existing colleague work", marker.read_text(encoding="utf-8"))
        self.assertEqual(["keep.txt"], sorted(item.name for item in self.destination.iterdir()))


if __name__ == "__main__":
    unittest.main()
