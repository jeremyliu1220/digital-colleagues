# SPDX-License-Identifier: Apache-2.0

"""Deterministic, allowlisted P8 release-candidate construction and inspection."""

from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = "0.1.0"
NODE_VERSION = "24.15.0"
NPM_VERSION = "11.12.1"
BASE_COMMIT = "df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc"
ACCEPTANCE_COMMIT = "eeb13ca643d5b512faab93e2e762ef4558dab688"
ARTIFACT_NAMES = (
    f"digital-colleagues-{VERSION}-source.tar.gz",
    f"digital_colleagues-{VERSION}-py3-none-any.whl",
    f"digital-colleagues-studio-{VERSION}.tar.gz",
    f"digital-colleagues-sbom-{VERSION}.json",
    f"digital-colleagues-release-manifest-{VERSION}.json",
    "SHA256SUMS",
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
LOCK_LINE = re.compile(r"^([A-Za-z0-9_.-]+)==([^ \\]+)")
HASH = re.compile(r"--hash=(sha256:[0-9a-f]{64})")
FORBIDDEN_ARCHIVE_PARTS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "node_modules",
}
FORBIDDEN_ARCHIVE_SUFFIXES = (
    ".backup",
    ".db",
    ".log",
    ".pyc",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
)


class ReleaseError(RuntimeError):
    """A release input or output failed a finite public-safe category."""


@dataclass(frozen=True)
class CandidateResult:
    source_commit: str
    source_timestamp: str
    artifacts: tuple[tuple[str, str], ...]


def _run(arguments: list[str], *, cwd: Path, environment: dict[str, str] | None = None) -> bytes:
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseError("release_subprocess_failed")
    return completed.stdout


def _git(root: Path, *arguments: str) -> str:
    return _run(["git", *arguments], cwd=root).decode("utf-8").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("release_json_invalid") from exc
    if not isinstance(value, dict):
        raise ReleaseError("release_json_invalid")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_epoch(root: Path, commit: str) -> int:
    value = _git(root, "show", "-s", "--format=%ct", commit)
    if not value.isdigit():
        raise ReleaseError("source_timestamp_invalid")
    return int(value)


def _policy(root: Path) -> dict[str, Any]:
    value = _json(root / "release/source-archive-policy.json")
    if (
        set(value)
        != {
            "schema_version",
            "allowed_root_files",
            "allowed_root_directories",
            "excluded_root_directories",
            "forbidden_components",
            "forbidden_suffixes",
        }
        or value.get("schema_version") != 1
    ):
        raise ReleaseError("source_archive_policy_invalid")
    if any(not isinstance(value[key], list) for key in value if key != "schema_version"):
        raise ReleaseError("source_archive_policy_invalid")
    return value


def _source_entries(root: Path, commit: str) -> tuple[tuple[str, str, str], ...]:
    policy = _policy(root)
    allowed_files = set(policy["allowed_root_files"])
    allowed_directories = set(policy["allowed_root_directories"])
    excluded_directories = set(policy["excluded_root_directories"])
    lines = _git(root, "ls-tree", "-r", "--full-tree", commit).splitlines()
    entries: list[tuple[str, str, str]] = []
    for line in lines:
        try:
            metadata, relative = line.split("\t", 1)
            mode, object_type, object_id = metadata.split(" ")
        except ValueError as exc:
            raise ReleaseError("source_tree_invalid") from exc
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ReleaseError("source_tree_invalid")
        if path.parts[0] in excluded_directories:
            continue
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ReleaseError("source_tree_special_entry")
        if len(path.parts) == 1:
            allowed = relative in allowed_files
        else:
            allowed = path.parts[0] in allowed_directories
        if (
            not allowed
            or any(part in set(policy["forbidden_components"]) for part in path.parts)
            or relative.endswith(tuple(policy["forbidden_suffixes"]))
        ):
            raise ReleaseError("source_archive_allowlist_failed")
        entries.append((relative, mode, object_id))
    if not entries or len(entries) != len(set(entries)):
        raise ReleaseError("source_tree_invalid")
    return tuple(sorted(entries))


def _tar_info(name: str, size: int, mode: int, epoch: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = epoch
    return info


def _write_normalized_tar(
    destination: Path,
    entries: tuple[tuple[str, bytes, int], ...],
    *,
    epoch: int,
) -> None:
    with destination.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name, content, mode in sorted(entries):
                    archive.addfile(_tar_info(name, len(content), mode, epoch), io.BytesIO(content))


def _source_archive(root: Path, commit: str, destination: Path, *, epoch: int) -> None:
    prefix = f"digital-colleagues-{VERSION}/"
    entries = tuple(
        (
            prefix + relative,
            _run(["git", "cat-file", "blob", object_id], cwd=root),
            0o755 if mode == "100755" else 0o644,
        )
        for relative, mode, object_id in _source_entries(root, commit)
    )
    _write_normalized_tar(destination, entries, epoch=epoch)


def _extract_source(archive_path: Path, destination: Path) -> Path:
    prefix = f"digital-colleagues-{VERSION}"
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise ReleaseError("source_archive_empty")
        for member in members:
            path = PurePosixPath(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != prefix
                or any(part in FORBIDDEN_ARCHIVE_PARTS for part in path.parts)
                or member.name.endswith(FORBIDDEN_ARCHIVE_SUFFIXES)
            ):
                raise ReleaseError("source_archive_member_invalid")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ReleaseError("source_archive_member_invalid")
            with target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(member.mode & 0o755)
    return destination / prefix


def _environment(epoch: int) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "SOURCE_DATE_EPOCH": str(epoch),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def _build_wheel(source: Path, output: Path, *, python: Path, environment: dict[str, str]) -> None:
    try:
        hatchling_version = importlib.metadata.version("hatchling")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ReleaseError("hatchling_unavailable") from exc
    if hatchling_version != "1.32.0":
        raise ReleaseError("hatchling_version_invalid")
    wheel_output = source.parent / "wheel-output"
    wheel_output.mkdir()
    _run(
        [str(python), "-B", "-m", "hatchling", "build", "-t", "wheel", "-d", str(wheel_output)],
        cwd=source,
        environment=environment,
    )
    wheels = tuple(wheel_output.glob("*.whl"))
    if len(wheels) != 1 or wheels[0].name != output.name:
        raise ReleaseError("wheel_identity_invalid")
    shutil.copyfile(wheels[0], output)


def _production_node_packages(package_lock: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    packages = package_lock.get("packages")
    if not isinstance(packages, dict):
        raise ReleaseError("studio_lock_invalid")
    result: list[tuple[str, str, str]] = []
    for path, value in packages.items():
        if not path or not isinstance(value, dict) or value.get("dev") is True:
            continue
        name = _npm_package_name(path)
        version = value.get("version")
        license_name = value.get("license")
        if not isinstance(version, str) or not isinstance(license_name, str):
            raise ReleaseError("studio_license_metadata_missing")
        result.append((name, version, license_name))
    return tuple(sorted(result))


def _third_party_licenses(studio: Path) -> bytes:
    package_lock = _json(studio / "package-lock.json")
    sections = [
        "Digital Colleagues Studio third-party license texts",
        f"Release candidate {VERSION}",
        "",
    ]
    for name, version, license_name in _production_node_packages(package_lock):
        license_path = studio / "node_modules" / name / "LICENSE"
        if license_path.is_symlink() or not license_path.is_file():
            raise ReleaseError("studio_license_text_missing")
        try:
            text = license_path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        except (OSError, UnicodeError) as exc:
            raise ReleaseError("studio_license_text_invalid") from exc
        sections.extend((f"--- {name} {version} ({license_name}) ---", text, ""))
    return ("\n".join(sections).rstrip() + "\n").encode("utf-8")


def _build_studio(source: Path, output: Path, *, epoch: int, environment: dict[str, str]) -> None:
    studio = source / "studio"
    node_version = _run(["node", "--version"], cwd=studio, environment=environment).decode().strip()
    npm_version = (
        _run(["corepack", "npm", "--version"], cwd=studio, environment=environment).decode().strip()
    )
    if node_version != f"v{NODE_VERSION}" or npm_version != NPM_VERSION:
        raise ReleaseError("npm_version_invalid")
    _run(
        ["corepack", "npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=studio,
        environment=environment,
    )
    _run(["corepack", "npm", "run", "build"], cwd=studio, environment=environment)
    dist = studio / "dist"
    if not dist.is_dir():
        raise ReleaseError("studio_build_missing")
    _write_json(
        dist / "build-toolchain.json",
        {"schema_version": 1, "node": NODE_VERSION, "npm": NPM_VERSION},
    )
    prefix = f"digital-colleagues-studio-{VERSION}/"
    entries: list[tuple[str, bytes, int]] = []
    for path in sorted(dist.rglob("*")):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ReleaseError("studio_build_special_entry")
        if path.is_file():
            relative = path.relative_to(dist).as_posix()
            entries.append((prefix + relative, path.read_bytes(), 0o644))
    entries.append((prefix + "THIRD_PARTY_LICENSES.txt", _third_party_licenses(studio), 0o644))
    _write_normalized_tar(output, tuple(entries), epoch=epoch)


def _parse_python_lock(path: Path) -> dict[tuple[str, str], tuple[str, ...]]:
    logical: list[str] = []
    current = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        current += (" " if current else "") + line.removesuffix("\\").strip()
        if not line.endswith("\\"):
            logical.append(current)
            current = ""
    if current:
        raise ReleaseError("python_lock_invalid")
    result: dict[tuple[str, str], tuple[str, ...]] = {}
    for line in logical:
        match = LOCK_LINE.match(line)
        hashes = tuple(sorted(set(HASH.findall(line))))
        if match is None or not hashes:
            raise ReleaseError("python_lock_invalid")
        key = (match.group(1).lower().replace("_", "-"), match.group(2))
        if key in result:
            raise ReleaseError("python_lock_invalid")
        result[key] = hashes
    return result


def _npm_package_name(path: str) -> str:
    marker = "node_modules/"
    if marker not in path:
        raise ReleaseError("studio_lock_path_invalid")
    candidate = path.rsplit(marker, 1)[1]
    parts = candidate.split("/")
    if (
        not candidate
        or any(not part or part in {".", ".."} for part in parts)
        or (candidate.startswith("@") and len(parts) != 2)
        or (not candidate.startswith("@") and len(parts) != 1)
    ):
        raise ReleaseError("studio_lock_path_invalid")
    return candidate


def build_supply_chain_inventory(root: Path, commit: str) -> dict[str, object]:
    inputs = _json(root / "release/supply-chain-inputs.json")
    if (
        set(inputs)
        != {
            "schema_version",
            "python",
            "docker_bases",
            "github_actions",
            "operator_tools",
        }
        or inputs.get("schema_version") != 1
    ):
        raise ReleaseError("supply_chain_inputs_invalid")
    python_lock = _parse_python_lock(root / "requirements/p8.lock")
    records: list[dict[str, object]] = []
    seen_python: set[tuple[str, str]] = set()
    for item in inputs["python"]:
        if not isinstance(item, dict) or set(item) != {"name", "version", "license", "role"}:
            raise ReleaseError("python_inventory_invalid")
        name = str(item["name"]).lower().replace("_", "-")
        version = str(item["version"])
        key = (name, version)
        hashes = python_lock.get(key)
        if hashes is None:
            raise ReleaseError("python_inventory_drift")
        seen_python.add(key)
        records.append(
            {
                "ecosystem": "python",
                "name": name,
                "version": version,
                "source_class": "pypi_hash_locked_wheel",
                "immutable_references": list(hashes),
                "declared_license": item["license"],
                "role": item["role"],
                "included_in_release_artifact": False,
                "attribution_treatment": "package_manager_dependency_not_bundled",
            }
        )
    if seen_python != set(python_lock):
        raise ReleaseError("python_inventory_drift")
    package = _json(root / "studio/package.json")
    package_lock = _json(root / "studio/package-lock.json")
    direct_runtime = set(package.get("dependencies", {}))
    direct_development = set(package.get("devDependencies", {}))
    packages = package_lock.get("packages")
    if not isinstance(packages, dict):
        raise ReleaseError("studio_lock_invalid")
    for path, value in packages.items():
        if not path:
            continue
        if not isinstance(value, dict):
            raise ReleaseError("studio_lock_invalid")
        name = _npm_package_name(path)
        node_version = value.get("version")
        license_name = value.get("license")
        integrity = value.get("integrity")
        if (
            not isinstance(node_version, str)
            or not isinstance(license_name, str)
            or not isinstance(integrity, str)
            or not integrity.startswith("sha512-")
        ):
            raise ReleaseError("studio_lock_invalid")
        bundled = value.get("dev") is not True
        if name in direct_runtime:
            role = "direct_runtime"
        elif name in direct_development:
            role = "direct_development"
        elif bundled:
            role = "transitive_runtime"
        else:
            role = "transitive_development"
        records.append(
            {
                "ecosystem": "npm",
                "name": name,
                "version": node_version,
                "source_class": "npm_integrity_locked_package",
                "immutable_references": [integrity],
                "declared_license": license_name,
                "role": role,
                "included_in_release_artifact": bundled,
                "attribution_treatment": (
                    "studio_THIRD_PARTY_LICENSES.txt" if bundled else "build_only_not_distributed"
                ),
            }
        )
    for item in inputs["docker_bases"]:
        if not isinstance(item, dict):
            raise ReleaseError("docker_inventory_invalid")
        records.append(
            {
                "ecosystem": "oci",
                "name": item["name"],
                "version": item["version"],
                "source_class": "oci_manifest_list",
                "immutable_references": [item["digest"]],
                "declared_license": item["license"],
                "role": item["role"],
                "included_in_release_artifact": False,
                "attribution_treatment": "operational_image_not_distributed_by_p8",
            }
        )
    for item in inputs["github_actions"]:
        if not isinstance(item, dict):
            raise ReleaseError("action_inventory_invalid")
        records.append(
            {
                "ecosystem": "github_action",
                "name": item["name"],
                "version": item["version"],
                "source_class": "git_commit_pinned_action",
                "immutable_references": [item["commit"]],
                "declared_license": item["license"],
                "role": "ci",
                "included_in_release_artifact": False,
                "attribution_treatment": "ci_operator_dependency_not_distributed",
            }
        )
    for item in inputs["operator_tools"]:
        if not isinstance(item, dict):
            raise ReleaseError("operator_inventory_invalid")
        records.append(
            {
                "ecosystem": "operator_tool",
                "name": item["name"],
                "version": item["version"],
                "source_class": "external_operator_prerequisite",
                "immutable_references": [item["immutable_reference"]],
                "declared_license": item["license"],
                "role": "release_or_operation_tool",
                "included_in_release_artifact": False,
                "attribution_treatment": "operator_supplied_not_distributed",
            }
        )
    records.sort(key=lambda item: (str(item["ecosystem"]), str(item["name"]), str(item["version"])))
    return {
        "schema_version": 1,
        "release_version": VERSION,
        "source_commit": commit,
        "records": records,
        "notice_treatment": {
            "root_notice": "unchanged_project_notice",
            "studio_runtime_dependencies": "license_texts_in_studio_archive",
            "python_dependencies": "not_bundled_in_wheel",
            "oci_images": "not_distributed_by_p8",
        },
        "review_class": "declared_metadata_review_not_legal_advice",
    }


def _verify_versions(root: Path) -> None:
    try:
        python = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError("python_metadata_invalid") from exc
    studio = _json(root / "studio/package.json")
    lock = _json(root / "studio/package-lock.json")
    package_root = (
        lock.get("packages", {}).get("") if isinstance(lock.get("packages"), dict) else None
    )
    if (
        python.get("project", {}).get("version") != VERSION
        or studio.get("version") != VERSION
        or lock.get("version") != VERSION
        or not isinstance(package_root, dict)
        or package_root.get("version") != VERSION
    ):
        raise ReleaseError("release_version_inconsistent")


def _build_input_digests(root: Path) -> list[dict[str, str]]:
    paths = (
        "Dockerfile",
        "Dockerfile.p7",
        "migrations/manifest.json",
        "pyproject.toml",
        "release/source-archive-policy.json",
        "release/supply-chain-inputs.json",
        "requirements/p8.lock",
        "studio/Dockerfile",
        "studio/Dockerfile.p7",
        "studio/package-lock.json",
        "studio/package.json",
    )
    return [{"path": path, "digest": _sha256(root / path)} for path in paths]


def build_candidate(root: Path, output: Path, *, python: Path) -> CandidateResult:
    root = root.resolve()
    if output.exists() and any(output.iterdir()):
        raise ReleaseError("release_output_not_empty")
    output.mkdir(parents=True, exist_ok=True)
    if _git(root, "status", "--porcelain"):
        raise ReleaseError("release_tree_dirty")
    commit = _git(root, "rev-parse", "HEAD")
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ReleaseError("source_commit_invalid")
    _git(root, "merge-base", "--is-ancestor", BASE_COMMIT, commit)
    _git(root, "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, commit)
    _verify_versions(root)
    epoch = _source_epoch(root, commit)
    source_timestamp = datetime.fromtimestamp(epoch, UTC).isoformat().replace("+00:00", "Z")
    environment = _environment(epoch)
    source_archive = output / ARTIFACT_NAMES[0]
    _source_archive(root, commit, source_archive, epoch=epoch)
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-build-") as temporary:
        source = _extract_source(source_archive, Path(temporary))
        _build_wheel(source, output / ARTIFACT_NAMES[1], python=python, environment=environment)
        _build_studio(source, output / ARTIFACT_NAMES[2], epoch=epoch, environment=environment)
    sbom_path = output / ARTIFACT_NAMES[3]
    _write_json(sbom_path, build_supply_chain_inventory(root, commit))
    migration_digest = _sha256(root / "migrations/manifest.json")
    content_artifacts = [
        {"name": name, "sha256": _sha256(output / name), "bytes": (output / name).stat().st_size}
        for name in ARTIFACT_NAMES[:4]
    ]
    manifest = {
        "schema_version": 1,
        "release_version": VERSION,
        "source_commit": commit,
        "source_timestamp": source_timestamp,
        "migration_manifest_digest": migration_digest,
        "artifacts": content_artifacts,
        "build_inputs": _build_input_digests(root),
        "evidence_classes": {
            "release": "synthetic_offline",
            "human_evaluation": "not_evaluated",
            "live_provider": "not_evaluated",
            "five_minute_target": "not_evaluated",
        },
        "claim_exclusions": [
            "formal_release_or_publication",
            "production_readiness",
            "production_security_or_privacy",
            "named_provider_compatibility",
            "real_message_delivery",
            "human_evaluation",
            "five_minute_target",
            "post_v0_1_capabilities",
        ],
    }
    manifest_path = output / ARTIFACT_NAMES[4]
    _write_json(manifest_path, manifest)
    checksum_names = ARTIFACT_NAMES[:5]
    checksum_text = "".join(
        f"{_sha256(output / name).removeprefix('sha256:')}  {name}\n"
        for name in sorted(checksum_names)
    )
    (output / ARTIFACT_NAMES[5]).write_text(checksum_text, encoding="ascii")
    result = validate_candidate(output, expected_commit=commit)
    return CandidateResult(commit, source_timestamp, tuple(sorted(result.items())))


def validate_candidate(output: Path, *, expected_commit: str | None = None) -> dict[str, str]:
    names = tuple(sorted(path.name for path in output.iterdir() if path.is_file()))
    if names != tuple(sorted(ARTIFACT_NAMES)):
        raise ReleaseError("release_artifact_set_invalid")
    manifest = _json(output / ARTIFACT_NAMES[4])
    if (
        manifest.get("schema_version") != 1
        or manifest.get("release_version") != VERSION
        or (expected_commit is not None and manifest.get("source_commit") != expected_commit)
    ):
        raise ReleaseError("release_manifest_invalid")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or [item.get("name") for item in artifacts] != list(
        ARTIFACT_NAMES[:4]
    ):
        raise ReleaseError("release_manifest_invalid")
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"name", "sha256", "bytes"}:
            raise ReleaseError("release_manifest_invalid")
        path = output / str(item["name"])
        if item["sha256"] != _sha256(path) or item["bytes"] != path.stat().st_size:
            raise ReleaseError("release_artifact_digest_invalid")
    expected_lines = {
        f"{_sha256(output / name).removeprefix('sha256:')}  {name}" for name in ARTIFACT_NAMES[:5]
    }
    try:
        actual_lines = set((output / ARTIFACT_NAMES[5]).read_text(encoding="ascii").splitlines())
    except (OSError, UnicodeError) as exc:
        raise ReleaseError("release_checksums_invalid") from exc
    if actual_lines != expected_lines or len(actual_lines) != len(ARTIFACT_NAMES[:5]):
        raise ReleaseError("release_checksums_invalid")
    for archive_name in (ARTIFACT_NAMES[0], ARTIFACT_NAMES[2]):
        with tarfile.open(output / archive_name, mode="r:gz") as archive:
            archive_members = {member.name for member in archive.getmembers()}
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                if (
                    not member.isfile()
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or any(part in FORBIDDEN_ARCHIVE_PARTS for part in member_path.parts)
                    or member.name.endswith(FORBIDDEN_ARCHIVE_SUFFIXES)
                ):
                    raise ReleaseError("release_archive_member_invalid")
            if archive_name == ARTIFACT_NAMES[0]:
                prefix = f"digital-colleagues-{VERSION}/"
                required_source_members = {
                    prefix + "compose.yaml",
                    prefix + "Dockerfile",
                    prefix + "requirements/p8.lock",
                    prefix + "studio/Dockerfile",
                    prefix + "studio/package-lock.json",
                }
                if not required_source_members.issubset(archive_members):
                    raise ReleaseError("release_source_runtime_incomplete")
    with zipfile.ZipFile(output / ARTIFACT_NAMES[1]) as wheel:
        if any(
            name.startswith("/") or ".." in PurePosixPath(name).parts for name in wheel.namelist()
        ):
            raise ReleaseError("wheel_member_invalid")
    return {name: _sha256(output / name) for name in ARTIFACT_NAMES}
