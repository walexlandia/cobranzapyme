"""Create a deterministic dependency inventory from committed manifests."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release" / "dependency-inventory.json"
SOURCES = (
    ROOT / "backend" / "requirements.txt",
    ROOT / "web" / "package.json",
    ROOT / "web" / "package-lock.json",
    ROOT / "compose.yaml",
    ROOT / "compose.secure.yaml",
    ROOT / "compose.pilot.yaml",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python_dependencies() -> list[dict[str, str]]:
    dependencies = []
    for line in (ROOT / "backend" / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        name = re.split(r"[<>=!~\[]", value, maxsplit=1)[0]
        dependencies.append({"name": name, "constraint": value})
    return sorted(dependencies, key=lambda item: item["name"].lower())


def _npm_dependencies() -> list[dict[str, Any]]:
    lock = json.loads((ROOT / "web" / "package-lock.json").read_text(encoding="utf-8"))
    direct = set(lock["packages"][""].get("dependencies", {}))
    dependencies = []
    for package_path, metadata in lock["packages"].items():
        if not package_path:
            continue
        name = package_path.removeprefix("node_modules/")
        dependencies.append(
            {
                "name": name,
                "version": metadata.get("version"),
                "direct": name in direct,
                "optional": bool(metadata.get("optional", False)),
                "integrity": metadata.get("integrity"),
                "license": metadata.get("license"),
            }
        )
    return sorted(dependencies, key=lambda item: item["name"].lower())


def _container_images() -> list[dict[str, Any]]:
    found: dict[str, set[str]] = {}
    for path in SOURCES:
        if not path.name.startswith("compose"):
            continue
        for match in re.finditer(r"^\s*image:\s*([^\s#]+)", path.read_text(encoding="utf-8"), re.M):
            image = match.group(1)
            found.setdefault(image, set()).add(path.name)
    return [
        {
            "image": image,
            "declared_in": sorted(files),
            "immutable": "@sha256:" in image,
        }
        for image, files in sorted(found.items())
    ]


def build_inventory() -> dict[str, Any]:
    missing = [str(path.relative_to(ROOT)) for path in SOURCES if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan manifiestos: " + ", ".join(missing))
    npm = _npm_dependencies()
    images = _container_images()
    return {
        "schema_version": "dependency-inventory-v1",
        "sources": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha256(path)}
            for path in SOURCES
        ],
        "python_direct": _python_dependencies(),
        "npm": {
            "lockfile_version": 3,
            "package_count": len(npm),
            "packages": npm,
        },
        "container_images": images,
        "unresolved_risks": [
            "Python usa rangos de versión; falta un lock con hashes para build reproducible.",
            "Las imágenes sin digest SHA-256 deben fijarse antes de un despliegue real.",
            "El inventario no sustituye un análisis de vulnerabilidades actualizado.",
        ],
    }


def serialized_inventory() -> bytes:
    return (
        json.dumps(build_inventory(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = serialized_inventory()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
            print("FAIL dependency inventory is missing or stale")
            return 1
        print("PASS dependency inventory is current")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
