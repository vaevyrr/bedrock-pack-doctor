import json
import tempfile
import unittest
from pathlib import Path
from packdoctor import PackDoctor

class PackDoctorTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = {
                "format_version": 2,
                "header": {"name": "Test", "description": "Pack",
                           "uuid": "a2f3e5d1-1c4a-4b2a-9b01-0c5a6b7d8e90", "version": [1, 0, 0]},
                "modules": [{"type": "resources",
                             "uuid": "b2f3e5d1-1c4a-4b2a-9b01-0c5a6b7d8e90", "version": [1, 0, 0]}]
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            doctor = PackDoctor()
            doctor.scan(root)
            self.assertEqual(doctor.report()["summary"]["error"], 0)

    def test_missing_manifest_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            doctor = PackDoctor()
            doctor.scan(Path(temp))
            self.assertGreater(doctor.report()["summary"]["error"], 0)

    def test_duplicate_uuid_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            same = "a2f3e5d1-1c4a-4b2a-9b01-0c5a6b7d8e90"
            manifest = {"format_version": 2,
                "header": {"name": "x", "description": "x", "uuid": same, "version": [1, 0, 0]},
                "modules": [{"uuid": same, "version": [1, 0, 0]}]}
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            doctor = PackDoctor()
            doctor.scan(root)
            self.assertTrue(any("Duplicate UUID" in f.message for f in doctor.findings))

if __name__ == "__main__":
    unittest.main()
