from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / "deployment"
STALE_IMAGE_TAGS = {"dev-31f2cae-r3"}
sys.path.insert(0, str(DEPLOYMENT))

import sync_assets  # noqa: E402


class TestAssetSync(unittest.TestCase):
	def test_sync_replaces_stale_assets_and_preserves_symlinks(self):
		with tempfile.TemporaryDirectory() as directory:
			base = Path(directory)
			source = base / "source"
			target = base / "target"
			bundle = source / "frappe" / "dist" / "css" / "desk.bundle.NEW.css"
			bundle.parent.mkdir(parents=True)
			bundle.write_text("new", encoding="utf-8")
			(source / "assets.json").write_text(
				json.dumps({"desk.bundle.css": "/assets/frappe/dist/css/desk.bundle.NEW.css"}),
				encoding="utf-8",
			)
			(source / "assets-rtl.json").write_text("{}", encoding="utf-8")
			target.mkdir()
			(target / "stale.css").write_text("stale", encoding="utf-8")

			with patch.object(sync_assets.shutil, "copytree", wraps=sync_assets.shutil.copytree) as copytree:
				sync_assets.sync(source, target)

			self.assertFalse((target / "stale.css").exists())
			self.assertTrue(any(call.kwargs.get("symlinks") for call in copytree.call_args_list))
			self.assertEqual("new", (target / "frappe" / "dist" / "css" / "desk.bundle.NEW.css").read_text())

	def test_sync_rejects_a_missing_manifest_target_before_clearing(self):
		with tempfile.TemporaryDirectory() as directory:
			base = Path(directory)
			source = base / "source"
			target = base / "target"
			source.mkdir()
			target.mkdir()
			(source / "assets.json").write_text(
				json.dumps({"desk.bundle.css": "/assets/frappe/dist/css/missing.css"}),
				encoding="utf-8",
			)
			(source / "assets-rtl.json").write_text("{}", encoding="utf-8")
			(target / "keep.css").write_text("keep", encoding="utf-8")

			with self.assertRaisesRegex(ValueError, "missing"):
				sync_assets.sync(source, target)

			self.assertTrue((target / "keep.css").exists())

	def test_sync_rejects_directory_manifest_target_before_clearing(self):
		with tempfile.TemporaryDirectory() as directory:
			base = Path(directory)
			source = base / "source"
			target = base / "target"
			(source / "frappe" / "dist" / "css" / "desk.bundle.DIR.css").mkdir(parents=True)
			(source / "assets.json").write_text(
				json.dumps({"desk.bundle.css": "/assets/frappe/dist/css/desk.bundle.DIR.css"}),
				encoding="utf-8",
			)
			(source / "assets-rtl.json").write_text("{}", encoding="utf-8")
			target.mkdir()
			(target / "keep.css").write_text("keep", encoding="utf-8")

			with self.assertRaisesRegex(ValueError, "must be a file"):
				sync_assets.sync(source, target)

			self.assertTrue((target / "keep.css").exists())

	def test_sync_rejects_symlink_manifest_target_before_clearing(self):
		with tempfile.TemporaryDirectory() as directory:
			base = Path(directory)
			source = base / "source"
			target = base / "target"
			bundle = source / "frappe" / "dist" / "css" / "desk.bundle.LINK.css"
			bundle.parent.mkdir(parents=True)
			real_bundle = source / "real.css"
			real_bundle.write_text("real", encoding="utf-8")
			try:
				bundle.symlink_to(real_bundle)
			except OSError as exc:
				self.skipTest(f"symlinks unavailable: {exc}")
			(source / "assets.json").write_text(
				json.dumps({"desk.bundle.css": "/assets/frappe/dist/css/desk.bundle.LINK.css"}),
				encoding="utf-8",
			)
			(source / "assets-rtl.json").write_text("{}", encoding="utf-8")
			target.mkdir()
			(target / "keep.css").write_text("keep", encoding="utf-8")

			with self.assertRaisesRegex(ValueError, "must not be a symlink"):
				sync_assets.sync(source, target)

			self.assertTrue((target / "keep.css").exists())


class TestComposeAssetContract(unittest.TestCase):
	def test_editable_stack_syncs_source_and_validates_repair_bundle(self):
		compose = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
		self.assertIn('dest_dir="apps/auto_service_management"', compose)
		self.assertIn('tmp_dir="apps/.auto_service_management.sync"', compose)
		self.assertIn('rm -rf "$$dest_dir"', compose)
		self.assertIn('mv "$$tmp_dir" "$$dest_dir"', compose)
		self.assertIn('test -f "sites/assets/$$bundle_path"', compose)

	def _render(self, compose_file: Path) -> dict:
		env = os.environ | {
			"DB_ROOT_PASSWORD": "contract-db-password",
			"ADMIN_PASSWORD": "contract-admin-password",
			"SITE_NAME": "contract.localhost",
			"CUSTOM_IMAGE": "registry.invalid/dms:contract",
		}
		result = subprocess.run(
			["docker", "compose", "-f", str(compose_file), "config", "--format", "json"],
			cwd=ROOT,
			env=env,
			check=True,
			capture_output=True,
			text=True,
		)
		return json.loads(result.stdout)

	def test_local_and_dokploy_stacks_gate_startup_on_matching_assets(self):
		for compose_file in (
			ROOT / "docker-compose.image.yml",
			DEPLOYMENT / "docker-compose.dokploy.yml",
		):
			with self.subTest(compose_file=compose_file.name):
				config = self._render(compose_file)
				services = config["services"]
				sync = services["assets-sync"]
				self.assertEqual("registry.invalid/dms:contract", sync["image"])
				self.assertEqual("0:0", sync["user"])
				self.assertIn("/usr/local/bin/sync-assets", sync["command"][-1])
				self.assertIn("/opt/frappe-assets/assets.json", sync["command"][-1])
				self.assertEqual(
					"service_completed_successfully",
					services["configurator"]["depends_on"]["assets-sync"]["condition"],
				)
				self.assertTrue(any(volume["target"] == "/target-assets" for volume in sync["volumes"]))
				self.assertFalse(any(volume["target"].endswith("/sites") for volume in sync["volumes"]))
				if compose_file.name == "docker-compose.dokploy.yml":
					self.assertNotIn("configs", sync)

				for service_name, service in services.items():
					if service_name not in {"db", "redis-cache", "redis-queue", "redis-socketio"}:
						self.assertEqual(
							"registry.invalid/dms:contract",
							service["image"],
							f"{service_name} must use CUSTOM_IMAGE",
						)

	def test_image_contains_an_unmasked_asset_seed(self):
		containerfile = (DEPLOYMENT / "Containerfile").read_text(encoding="utf-8")
		self.assertIn("/opt/frappe-assets", containerfile)
		self.assertIn("sync_assets.py", containerfile)

	def test_image_build_checks_out_the_pinned_upstream_commits(self):
		containerfile = (DEPLOYMENT / "Containerfile").read_text(encoding="utf-8")
		for branch, commit in (
			("version-16", "FRAPPE_COMMIT"),
			("version-16", "ERPNEXT_COMMIT"),
			("version-16", "HRMS_COMMIT"),
			("hotfix-v-16", "UGANDA_COMPLIANCE_COMMIT"),
		):
			with self.subTest(branch=branch, commit=commit):
				self.assertIn(f"update-ref refs/heads/{branch} \"${{{commit}}}\"", containerfile)

	def test_environment_contract_has_one_dms_image_variable(self):
		env_example = (DEPLOYMENT / "image.env.example").read_text(encoding="utf-8")
		self.assertIn("CUSTOM_IMAGE=", env_example)
		self.assertNotIn("SOCKETIO_IMAGE=", env_example)
		self.assertNotIn("NGINX_IMAGE=", env_example)

	def test_image_stack_requires_explicit_non_stale_immutable_tag(self):
		local_compose = (ROOT / "docker-compose.image.yml").read_text(encoding="utf-8")
		env_example = (DEPLOYMENT / "image.env.example").read_text(encoding="utf-8")

		self.assertIn("${CUSTOM_IMAGE:?", local_compose)
		self.assertIn("CUSTOM_IMAGE=aslamkimb/frappe-dms-ug:dev-<short-sha>", env_example)
		for stale_tag in STALE_IMAGE_TAGS:
			self.assertNotIn(stale_tag, local_compose)
			self.assertNotIn(stale_tag, env_example)


if __name__ == "__main__":
	unittest.main()
