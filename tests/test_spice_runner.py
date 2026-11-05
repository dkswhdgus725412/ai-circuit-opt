"""Portable simulator discovery tests; run with python -m unittest discover -s tests."""

import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import spice_runner

ROOT = Path(__file__).resolve().parents[1]


class DiscoveryTests(unittest.TestCase):
    def test_linux_uses_native_ngspice(self):
        with patch.object(spice_runner, "os", SimpleNamespace(name="posix", environ={})), \
             patch.object(spice_runner.shutil, "which", return_value="/usr/bin/ngspice") as which:
            self.assertEqual(spice_runner.find_ngspice(), "/usr/bin/ngspice")
            which.assert_called_once_with("ngspice")

    def test_explicit_path_takes_priority(self):
        env = {"NGSPICE_PATH": "/custom path/ngspice"}
        with patch.dict(os.environ, env), \
             patch.object(spice_runner.shutil, "which", return_value=env["NGSPICE_PATH"]) as which:
            self.assertEqual(spice_runner.find_ngspice(), env["NGSPICE_PATH"])
            which.assert_called_once_with(env["NGSPICE_PATH"])

    def test_invalid_override_is_not_silently_ignored(self):
        with patch.dict(os.environ, {"NGSPICE_PATH": "/missing/ngspice"}), \
             patch.object(spice_runner.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "NGSPICE_PATH"):
                spice_runner.find_ngspice()

    def test_windows_prefers_console(self):
        with patch.object(spice_runner, "os", SimpleNamespace(name="nt", environ={})), \
             patch.object(spice_runner.shutil, "which", return_value="console.exe") as which:
            self.assertEqual(spice_runner.find_ngspice(), "console.exe")
            which.assert_called_once_with("ngspice_con")

    def test_windows_default_location_still_supported(self):
        with patch.object(spice_runner, "os", SimpleNamespace(name="nt", environ={})), \
             patch.object(spice_runner.shutil, "which", return_value=None), \
             patch.object(spice_runner, "Path") as path:
            path.return_value.is_file.return_value = True
            self.assertEqual(spice_runner.find_ngspice(), r"C:\Spice64\bin\ngspice_con.exe")

    def test_missing_binary_has_arch_instructions(self):
        with patch.object(spice_runner, "os", SimpleNamespace(name="posix", environ={})), \
             patch.object(spice_runner.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "pacman"):
                spice_runner.find_ngspice()


class SimulationTests(unittest.TestCase):
    def test_batch_execution_controls_locale_and_encoding(self):
        proc = subprocess.CompletedProcess([], 0, "Measurements for AC Analysis\nfc = 1587.8\n", "")
        with patch.object(spice_runner, "find_ngspice", return_value="/usr/bin/ngspice"), \
             patch.object(spice_runner.subprocess, "run", return_value=proc) as run:
            metrics, _ = spice_runner.run_simulation(
                ROOT / "circuits/rc_lowpass.cir", {"R": 1000, "C": 1e-7}, timeout=7
            )
            self.assertEqual(metrics["fc"], 1587.8)
            args, kwargs = run.call_args
            self.assertEqual(args[0][:2], ["/usr/bin/ngspice", "-b"])
            self.assertEqual(kwargs["env"]["LC_ALL"], "C")
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(kwargs["timeout"], 7)

    @unittest.skipUnless(shutil.which("ngspice"), "ngspice not installed")
    def test_real_rc_with_unicode_and_spaces_in_template_path(self):
        with tempfile.TemporaryDirectory(prefix="회로 test ") as tmp:
            template = Path(tmp) / "저역 필터.cir"
            shutil.copyfile(ROOT / "circuits/rc_lowpass.cir", template)
            metrics, output = spice_runner.run_simulation(template, {"R": 1000, "C": 1e-7})
            self.assertIn("fc", metrics, output)
            self.assertLess(abs(metrics["fc"] / (1 / (2 * math.pi * 1000 * 1e-7)) - 1), 0.01)
            self.assertIn("gain_10k", metrics)


if __name__ == "__main__":
    unittest.main()
