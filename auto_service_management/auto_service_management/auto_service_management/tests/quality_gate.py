"""Static test-discovery checks used by local and CI quality gates.

This module deliberately uses only the Python standard library.  It catches
duplicate test identities before Frappe's runner starts importing the suite,
where an import collision otherwise tends to look like a missing or silently
skipped test.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


class TestDiscoveryError(ValueError):
	"""Raised when the app's test tree cannot be discovered safely."""


@dataclass(frozen=True)
class TestCaseIdentity:
	"""A stable, import-qualified identity for one discovered test method."""

	module: str
	owner: str | None
	name: str

	@property
	def qualified_name(self) -> str:
		owner = f"{self.owner}." if self.owner else ""
		return f"{self.module}.{owner}{self.name}"


@dataclass(frozen=True)
class TestDiscovery:
	"""Deterministic inventory returned by :func:`discover_tests`."""

	modules: tuple[str, ...]
	cases: tuple[TestCaseIdentity, ...]


class _TestCaseVisitor(ast.NodeVisitor):
	def __init__(self, module: str):
		self.module = module
		self.owner_stack: list[str] = []
		self.cases: list[TestCaseIdentity] = []

	def visit_ClassDef(self, node: ast.ClassDef):
		self.owner_stack.append(node.name)
		self.generic_visit(node)
		self.owner_stack.pop()

	def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
		if isinstance(node, ast.FunctionDef) and node.name.startswith("test_") and len(self.owner_stack) == 1:
			self.cases.append(
				TestCaseIdentity(
					module=self.module,
					owner=".".join(self.owner_stack),
					name=node.name,
				)
			)
		# Do not descend into method bodies: nested helpers are not test cases.

	visit_FunctionDef = _visit_function

	def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
		# unittest/Frappe do not execute async methods as regular test cases.
		return None


def _module_name(test_file: Path, package_root: Path) -> str:
	try:
		relative = test_file.relative_to(package_root.parent).with_suffix("")
	except ValueError as exc:
		raise TestDiscoveryError(f"Test file is outside package root: {test_file}") from exc
	return ".".join(relative.parts)


def discover_tests(package_root: Path | str) -> TestDiscovery:
	"""Discover test modules and reject duplicate import-qualified test IDs."""

	package_root = Path(package_root).resolve()
	if not package_root.is_dir():
		raise TestDiscoveryError(f"Package root does not exist: {package_root}")

	test_files = tuple(sorted(package_root.rglob("test_*.py")))
	if not test_files:
		raise TestDiscoveryError(f"No test modules found below {package_root}")

	modules: list[str] = []
	cases: list[TestCaseIdentity] = []
	for test_file in test_files:
		module = _module_name(test_file, package_root)
		modules.append(module)
		try:
			tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
		except (OSError, SyntaxError) as exc:
			raise TestDiscoveryError(f"Could not parse {test_file}: {exc}") from exc
		visitor = _TestCaseVisitor(module)
		visitor.visit(tree)
		if not visitor.cases:
			raise TestDiscoveryError(f"Test module has no discoverable test methods: {module}")
		cases.extend(visitor.cases)

	duplicate_modules = sorted(name for name, count in Counter(modules).items() if count > 1)
	duplicate_cases = sorted(
		name for name, count in Counter(case.qualified_name for case in cases).items() if count > 1
	)
	if duplicate_modules or duplicate_cases:
		issues = []
		if duplicate_modules:
			issues.append(f"duplicate modules: {', '.join(duplicate_modules)}")
		if duplicate_cases:
			issues.append(f"duplicate test IDs: {', '.join(duplicate_cases)}")
		raise TestDiscoveryError("; ".join(issues))

	return TestDiscovery(modules=tuple(modules), cases=tuple(cases))


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--package-root",
		type=Path,
		default=Path(__file__).resolve().parents[2],
		help="App package root recursively scanned by Frappe's test loader (default: inferred)",
	)
	args = parser.parse_args(argv)
	try:
		discovery = discover_tests(args.package_root)
	except TestDiscoveryError as exc:
		print(f"FAIL: test discovery guard: {exc}", file=sys.stderr)
		return 1
	print(
		f"PASS: discovered {len(discovery.modules)} test modules and "
		f"{len(discovery.cases)} unique test IDs under {Path(args.package_root).resolve()}"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
