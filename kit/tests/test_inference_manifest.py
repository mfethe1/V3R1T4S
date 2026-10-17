import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from check_inference_manifest import validate


class InferenceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = json.loads((Path(__file__).parents[1] / "INFERENCE_EXPERIMENT.json").read_text())
        cls.template["workload"]["request_set_sha256"] = "sha256:" + "a" * 64
        cls.template["measurements"]["raw_results_sha256"] = "sha256:" + "b" * 64
        for arm in ("baseline", "intervention"):
            cls.template["arms"][arm]["configuration_sha256"] = "sha256:" + "c" * 64

    def test_each_arm_rejects_invalid_configuration_hash(self):
        invalid = [None, "", "sha256:replace-with-64-hex-digits", "not-a-hash",
                   "sha256:" + "a" * 63, "sha256:" + "a" * 65,
                   "sha256:" + "A" * 64, "sha256:" + "g" * 64, 123, {}]
        for arm in ("baseline", "intervention"):
            for value in invalid:
                with self.subTest(arm=arm, value=value):
                    manifest = copy.deepcopy(self.template)
                    manifest["arms"][arm]["configuration_sha256"] = value
                    self.assertTrue(any(f"arms.{arm}.configuration_sha256" in e
                                        for e in validate(manifest)))

    def test_missing_configuration_hash_is_rejected(self):
        for arm in ("baseline", "intervention"):
            with self.subTest(arm=arm):
                manifest = copy.deepcopy(self.template)
                del manifest["arms"][arm]["configuration_sha256"]
                self.assertTrue(any(f"arms.{arm}.configuration_sha256" in e
                                    for e in validate(manifest)))

    def test_malformed_arms_are_errors_not_tracebacks(self):
        for value in (None, [], "not-an-object", 1):
            with self.subTest(value=value):
                manifest = copy.deepcopy(self.template)
                manifest["arms"] = value
                self.assertIn("arms must be an object", validate(manifest))
        for arm in ("baseline", "intervention"):
            for value in (None, [], "not-an-object", 1):
                with self.subTest(arm=arm, value=value):
                    manifest = copy.deepcopy(self.template)
                    manifest["arms"][arm] = value
                    self.assertIn(f"arms.{arm} must be an object", validate(manifest))

    def test_template_with_realistic_hash_placeholders_passes_bookkeeping(self):
        self.assertEqual([], validate(copy.deepcopy(self.template)))

    def test_bad_hash_and_unmatched_measurement_requirements_fail(self):
        manifest = copy.deepcopy(self.template)
        manifest["workload"]["request_set_sha256"] = "not-a-hash"
        manifest["measurements"]["record_per_request"] = False
        errors = validate(manifest)
        self.assertTrue(any("request_set_sha256" in e for e in errors))
        self.assertTrue(any("record_per_request" in e for e in errors))

    def test_nonpositive_workload_is_rejected(self):
        manifest = copy.deepcopy(self.template)
        manifest["workload"]["concurrency"] = 0
        self.assertIn("workload.concurrency must be a positive integer", validate(manifest))


if __name__ == "__main__":
    unittest.main()
