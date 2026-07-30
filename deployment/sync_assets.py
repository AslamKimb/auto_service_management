#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
from urllib.parse import urlsplit


MANIFESTS = ("assets.json", "assets-rtl.json")


def validate(root: Path) -> int:
	count = 0
	for manifest_name in MANIFESTS:
		manifest = root / manifest_name
		if not manifest.is_file():
			raise ValueError(f"{manifest} is missing")

		data = json.loads(manifest.read_text(encoding="utf-8"))
		if not isinstance(data, dict):
			raise ValueError(f"{manifest} must contain an object")

		for logical_name, value in data.items():
			if not isinstance(value, str):
				raise ValueError(f"{manifest}: {logical_name} must map to a string")

			url_path = urlsplit(value).path
			if not url_path.startswith("/assets/"):
				raise ValueError(f"{manifest}: {logical_name} has invalid path {value}")

			relative = PurePosixPath(url_path.removeprefix("/assets/"))
			if ".." in relative.parts:
				raise ValueError(f"{manifest}: {logical_name} escapes the assets directory")

			asset = root.joinpath(*relative.parts)
			if not asset.exists():
				raise ValueError(f"{manifest}: {logical_name} target {asset} is missing")
			if asset.is_symlink():
				raise ValueError(f"{manifest}: {logical_name} target {asset} must not be a symlink")
			if not asset.is_file():
				raise ValueError(f"{manifest}: {logical_name} target {asset} must be a file")
			count += 1
	return count


def sync(source: Path | str, target: Path | str) -> int:
	source = Path(source).resolve(strict=True)
	target = Path(target).resolve()
	if source == target or target == Path(target.anchor):
		raise ValueError(f"unsafe asset target: {target}")

	count = validate(source)
	target.mkdir(parents=True, exist_ok=True)
	for child in target.iterdir():
		if child.is_symlink() or child.is_file():
			child.unlink()
		else:
			shutil.rmtree(child)
	shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
	validate(target)
	return count


def main() -> None:
	parser = argparse.ArgumentParser(description="Replace a Frappe assets volume from an image-owned seed")
	parser.add_argument("source", type=Path)
	parser.add_argument("target", type=Path)
	args = parser.parse_args()
	count = sync(args.source, args.target)
	print(f"Synchronized {count} manifest assets from {args.source} to {args.target}")


if __name__ == "__main__":
	main()
