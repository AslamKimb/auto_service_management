from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .quality_gate import TestDiscoveryError, discover_tests


class TestPhase33QualityGate(unittest.TestCase):
	def test_discovery_returns_stable_modules_and_case_ids(self):
		with tempfile.TemporaryDirectory() as temporary_directory:
			package_root = Path(temporary_directory) / "pkg"
			test_file = package_root / "tests" / "test_sample.py"
			test_file.parent.mkdir(parents=True)
			test_file.write_text(
				"class TestSample:\n"
				"    def test_second(self):\n"
				"        pass\n"
				"    def test_first(self):\n"
				"        pass\n",
				encoding="utf-8",
			)

			discovery = discover_tests(package_root)

		self.assertEqual(("pkg.tests.test_sample",), discovery.modules)
		self.assertEqual(
			(
				"pkg.tests.test_sample.TestSample.test_second",
				"pkg.tests.test_sample.TestSample.test_first",
			),
			tuple(case.qualified_name for case in discovery.cases),
		)

	def test_duplicate_test_method_is_rejected_before_runner(self):
		with tempfile.TemporaryDirectory() as temporary_directory:
			package_root = Path(temporary_directory) / "pkg"
			test_file = package_root / "tests" / "test_duplicate.py"
			test_file.parent.mkdir(parents=True)
			test_file.write_text(
				"class TestDuplicate:\n"
				"    def test_same(self):\n"
				"        pass\n"
				"    def test_same(self):\n"
				"        pass\n",
				encoding="utf-8",
			)

			with self.assertRaisesRegex(TestDiscoveryError, "duplicate test IDs"):
				discover_tests(package_root)

	def test_discovery_matches_frappe_app_root_and_excludes_nested_async_helpers(self):
		with tempfile.TemporaryDirectory() as temporary_directory:
			package_root = Path(temporary_directory) / "pkg"
			legacy_file = package_root / "tests" / "test_legacy.py"
			nested_file = package_root / "pkg" / "tests" / "test_nested.py"
			legacy_file.parent.mkdir(parents=True)
			nested_file.parent.mkdir(parents=True)
			legacy_file.write_text(
				"class TestLegacy:\n"
				"    def test_direct(self):\n"
				"        def test_helper():\n"
				"            pass\n"
				"        return test_helper\n"
				"    async def test_async(self):\n"
				"        pass\n"
				"class Outer:\n"
				"    class Inner:\n"
				"        def test_nested_class(self):\n"
				"            pass\n",
				encoding="utf-8",
			)
			nested_file.write_text(
				"class TestNested:\n    def test_nested(self):\n        pass\n",
				encoding="utf-8",
			)

			discovery = discover_tests(package_root)

		self.assertEqual(
			("pkg.pkg.tests.test_nested", "pkg.tests.test_legacy"),
			discovery.modules,
		)
		self.assertEqual(
			(
				"pkg.pkg.tests.test_nested.TestNested.test_nested",
				"pkg.tests.test_legacy.TestLegacy.test_direct",
			),
			tuple(case.qualified_name for case in discovery.cases),
		)
