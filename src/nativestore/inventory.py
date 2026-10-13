"""Collect installed Python dependency versions and actual license notices for staging."""

import json
import re
import shutil
import tomllib
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

from .errors import BuildError


def collect(root: Path, destination: Path) -> list[dict]:
    names = {"nativestore", "jinjax"}
    project_file = root / "pyproject.toml"
    if project_file.is_file():
        project = tomllib.loads(project_file.read_text()).get("project", {})
        names.update(Requirement(value).name for value in project.get("dependencies", []))
    discovered = {}
    pending = list(names)
    while pending:
        name = pending.pop()
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in discovered:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError as exc:
            raise BuildError(f"Application dependency is not installed: {name}") from exc
        notices: list[str] = []
        for package_file in distribution.files or []:
            if re.match(r"^(?:LICEN[CS]E|COPYING|NOTICE)(?:[._-].*)?$", package_file.name, re.I):
                source = Path(str(distribution.locate_file(package_file)))
                if not source.is_file():
                    continue
                target = destination / normalized / (str(len(notices)) + "-" + package_file.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                notices.append(target.relative_to(destination).as_posix())
        discovered[normalized] = {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
            "license": (
                distribution.metadata.get_all("License-Expression")
                or distribution.metadata.get_all("License")
                or ["Not declared"]
            )[0],
            "notices": notices,
        }
        for value in distribution.requires or []:
            requirement = Requirement(value)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    records = [discovered[key] for key in sorted(discovered)]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "python-dependencies.json").write_text(json.dumps(records, indent=2) + "\n")
    return records
