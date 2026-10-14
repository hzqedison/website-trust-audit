"""Execute the README installer with each locally available PowerShell engine."""

import base64
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")
WINDOWS_POWERSHELL = shutil.which("powershell.exe")


class InstallChecks:
    """Shared behavioral checks, inherited by two actual-engine test suites."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="website-trust-install-test-")
        self.sandbox = Path(self.temp.name)
        self.destination = self.sandbox / "安装 target [team] O'Brien" / "installed-skill"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"```powershell\s*\n(.*?)\n```", readme, re.S)
        self.assertIsNotNone(match, "README needs an executable PowerShell installation block")
        self.command = match.group(1)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def literal(path):
        return "'" + str(path).replace("'", "''") + "'"

    def install(self, source=ROOT, before="", after=""):
        # Replace only the destination line; never change CODEX_HOME or user settings.
        command, count = re.subn(
            r"(?m)^\$target\s*=.*$",
            lambda _: f"$target = {self.literal(self.destination)}",
            self.command,
        )
        self.assertEqual(1, count)
        # EncodedCommand preserves non-ASCII input on Windows PowerShell 5.1.
        # Console encoding is set only in this disposable child process.
        command = (
            "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding\n"
            # PS 5.1 may not retain a wildcard-looking startup cwd. The README
            # requires entering the package root before running its installer.
            + "Set-Location -LiteralPath " + self.literal(source) + " -ErrorAction Stop\n"
            + before + "\n" + command + "\n" + after
        )
        encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
        return subprocess.run(
            [self.engine, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            cwd=source, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )

    def make_source(self):
        source = self.sandbox / "来源 source [v1] O'Brien"
        source.mkdir()
        (source / "SKILL.md").write_text("# Synthetic skill 合成技能\n", encoding="utf-8")
        return source

    def test_copy_matches_source_and_excludes_runtime_files(self):
        result = self.install()
        self.assertEqual(0, result.returncode, result.stderr)
        excluded = {".git", "__pycache__", "evidence", "runs"}
        expected = {
            item.relative_to(ROOT).as_posix(): item.read_bytes()
            for item in ROOT.rglob("*")
            if item.is_file()
            and not excluded.intersection(item.relative_to(ROOT).parts)
            and item.suffix.lower() != ".pyc"
        }
        actual = {
            item.relative_to(self.destination).as_posix(): item.read_bytes()
            for item in self.destination.rglob("*") if item.is_file()
        }
        self.assertEqual(expected, actual)

    def test_literal_paths_and_nested_exclusions(self):
        source = self.make_source()
        expected = {
            "SKILL.md": (source / "SKILL.md").read_bytes(),
            "references/说明 [v1] O'Brien.md": "中文 evidence in a filename\n".encode("utf-8"),
            "assets/sample.bin": bytes(range(256)),
            "references/runs-not-excluded.txt": b"keep this similarly named file",
            ".gitignore": b"keep this hidden file",
        }
        for relative, content in expected.items():
            item = source / relative
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_bytes(content)
        for prefix in ("", "references/nested/"):
            for excluded in (".git", "__pycache__", "evidence", "runs"):
                item = source / prefix / excluded / "must-not-copy.txt"
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_bytes(b"excluded")
        for relative in ("cached.pyc", "references/CACHED.PYC"):
            (source / relative).write_bytes(b"excluded bytecode")
        result = self.install(source)
        self.assertEqual(0, result.returncode, result.stderr)
        actual = {
            item.relative_to(self.destination).as_posix(): item.read_bytes()
            for item in self.destination.rglob("*") if item.is_file()
        }
        self.assertEqual(expected, actual)

    def test_existing_install_is_preserved(self):
        self.destination.mkdir(parents=True)
        marker = self.destination / "keep.txt"
        marker.write_text("existing colleague work", encoding="utf-8")
        result = self.install()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("existing colleague work", marker.read_text(encoding="utf-8"))
        self.assertEqual(["keep.txt"], sorted(item.name for item in self.destination.iterdir()))

    def test_missing_skill_is_rejected_before_creating_target(self):
        source = self.sandbox / "not-a-skill"
        source.mkdir()
        result = self.install(source)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.destination.exists())

    def test_skill_directory_is_not_accepted_as_skill_file(self):
        source = self.sandbox / "invalid-skill"
        (source / "SKILL.md").mkdir(parents=True)
        result = self.install(source)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.destination.exists())

    def test_nested_destination_is_rejected_without_recursive_copy(self):
        source = self.make_source()
        self.destination = source / "nested" / "installed-skill"
        result = self.install(source)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.destination.exists())
        self.assertEqual(["SKILL.md"], sorted(item.name for item in source.iterdir()))

    def test_copy_failure_is_terminating(self):
        source = self.make_source()
        result = self.install(
            source,
            before=(
                "$locked = [IO.File]::Open("
                + self.literal(source / "SKILL.md")
                + ", [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)\n"
                "try {\n"
            ),
            after="Write-Output 'UNEXPECTED_INSTALL_SUCCESS'\n} finally { $locked.Dispose() }",
        )
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(self.destination.is_dir(), "Failure must occur during copying, not a prior guard")
        self.assertNotIn("UNEXPECTED_INSTALL_SUCCESS", result.stdout)
        self.assertEqual("# Synthetic skill 合成技能\n", (source / "SKILL.md").read_text(encoding="utf-8"))


@unittest.skipUnless(WINDOWS_POWERSHELL, "Windows PowerShell 5.1 is not available")
class WindowsPowerShellInstallTests(InstallChecks, unittest.TestCase):
    engine = WINDOWS_POWERSHELL


@unittest.skipUnless(PWSH, "PowerShell 7 is not available")
class PowerShell7InstallTests(InstallChecks, unittest.TestCase):
    engine = PWSH


if __name__ == "__main__":
    unittest.main()
