"""Unit tests for selector-based probe resolution."""
import importlib.util
import json
import pathlib
import subprocess
import unittest
from unittest.mock import patch

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run_exp001.py"
spec = importlib.util.spec_from_file_location("run_exp001", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def pod(name, ready=True, phase="Running"):
    return {"metadata": {"name": name}, "status": {"phase": phase, "conditions": [
        {"type": "Ready", "status": "True" if ready else "False"}
    ]}}


class ProbeTargetTests(unittest.TestCase):
    def select(self, items):
        with patch.object(module, "run", return_value=subprocess.CompletedProcess(
            [], 0, stdout=json.dumps({"items": items}), stderr=""
        )) as mocked:
            if len([p for p in items if p["status"]["phase"] == "Running"
                    and p["status"]["conditions"][0]["status"] == "True"]) == 1:
                result = module.probe_target("tenant-a")
                self.assertIn(result, [p["metadata"]["name"] for p in items])
            else:
                with self.assertRaises(RuntimeError):
                    module.probe_target("tenant-a")
            mocked.assert_called_once_with(
                "kubectl", "-n", "tenant-a", "get", "pods", "-l", "app=probe", "-o", "json"
            )

    def test_deployment_pod(self):
        self.select([pod("probe-abc-123")])

    def test_standalone_pod(self):
        self.select([pod("probe")])

    def test_unready(self):
        self.select([pod("probe-abc", ready=False)])

    def test_multiple_ready(self):
        self.select([pod("probe-a"), pod("probe-b")])

    def test_one_ready_among_unready(self):
        self.select([pod("probe-a", ready=False), pod("probe-b")])


if __name__ == "__main__":
    unittest.main()
