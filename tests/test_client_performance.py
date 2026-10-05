"""Bounded sampled browser performance metrics; no browser or database required."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ClientPerformanceTests(unittest.TestCase):
    def run_node(self, script):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / script)], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_sampled_performance_collection(self):
        self.run_node('client_performance.mjs')

    def test_api_phase_measurements(self):
        self.run_node('api_performance.mjs')


if __name__ == '__main__':
    unittest.main()
