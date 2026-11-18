#!/usr/bin/env python3
"""Release consistency checks for `how` (standard library only).

    python3 scripts/check_release.py            # versions agree + plugin manifest is valid
    python3 scripts/check_release.py v1.0.0     # ...and they equal this tag
    python3 scripts/check_release.py --bump 1.0.1   # write a new version into all files

Checks that the version is the same in:
  how (__version__), PKGBUILD (pkgver), .SRCINFO (pkgver), manifest.json (version),
  install.sh (HOW_DEFAULT_VERSION)
and validates manifest.json with the same rules as Omarchy's
`omarchy plugin validate` (schemaVersion 1, required fields, safe id, kinds,
entry points that are safe relative paths and exist, an entry point for each
kind that needs one, no symlinks in the plugin folder).
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def grab(name, pattern):
    match = re.search(pattern, read(name), re.MULTILINE)
    return match.group(1) if match else None


def versions():
    return {
        "how __version__": grab("how", r'^__version__\s*=\s*["\']([^"\']+)["\']'),
        "PKGBUILD pkgver": grab("PKGBUILD", r"^pkgver=(\S+)$"),
        ".SRCINFO pkgver": grab(".SRCINFO", r"^\s*pkgver = (\S+)$"),
        "manifest.json version": json.loads(read("manifest.json")).get("version"),
        "install.sh default": (grab("install.sh", r'^HOW_DEFAULT_VERSION="v?([^"]+)"$')),
    }


# Mirrors basecamp/omarchy bin/omarchy-plugin-validate.
KIND_ENTRY_POINTS = {
    "bar": "bar",
    "bar-widget": "barWidget",
    "menu": "menu",
    "overlay": "overlay",
    "panel": "panel",
    "service": "service",
}


def manifest_errors():
    errors = []
    try:
        manifest = json.loads(read("manifest.json"))
    except ValueError as exc:
        return ["manifest.json is not valid JSON: %s" % exc]
    if manifest.get("schemaVersion") != 1 or isinstance(manifest.get("schemaVersion"), bool):
        errors.append("schemaVersion must be the number 1")
    for field in ("id", "name", "version", "kinds", "entryPoints"):
        if field not in manifest:
            errors.append("missing required field '%s'" % field)
    plugin_id = str(manifest.get("id", ""))
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", plugin_id) or ".." in plugin_id:
        errors.append("invalid plugin id '%s'" % plugin_id)
    if plugin_id.startswith("omarchy."):
        errors.append("plugin id uses the reserved omarchy.* namespace")
    kinds = manifest.get("kinds")
    if not isinstance(kinds, list) or not kinds:
        errors.append("'kinds' must be a non-empty array")
        kinds = []
    entry_points = manifest.get("entryPoints")
    if not isinstance(entry_points, dict):
        errors.append("'entryPoints' must be an object")
        entry_points = {}
    for key, path in entry_points.items():
        path = str(path)
        if not path or "\n" in path or path.startswith("/") or ".." in path:
            errors.append("unsafe entry point %s=%r" % (key, path))
        elif not os.path.isfile(os.path.join(ROOT, path)):
            errors.append("entry point file not found: %s" % path)
    for kind, key in KIND_ENTRY_POINTS.items():
        if kind in kinds and key not in entry_points:
            errors.append("kind '%s' requires entryPoints.%s" % (kind, key))
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                errors.append("symlinks are not allowed in a plugin folder: %s" % os.path.relpath(full, ROOT))
    return errors


def bump(new):
    """Write version NEW into every file that carries it."""
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", new):
        raise SystemExit("version must look like 1.2.3, got %r" % new)
    old = versions()["PKGBUILD pkgver"]
    edits = {
        "how": [(r'^(__version__\s*=\s*)["\'][^"\']*["\']', r'\g<1>"%s"' % new)],
        "PKGBUILD": [(r"^pkgver=.*$", "pkgver=" + new), (r"^pkgrel=.*$", "pkgrel=1")],
        ".SRCINFO": [(r"^(\s*pkgver = ).*$", r"\g<1>" + new), (r"^(\s*pkgrel = ).*$", r"\g<1>1"),
                     (re.escape(old), new) if old else (r"(?!)", "")],
        "manifest.json": [(r'^(\s*"version":\s*)"[^"]*"', r'\g<1>"%s"' % new)],
        "install.sh": [(r'^HOW_DEFAULT_VERSION="[^"]*"$', 'HOW_DEFAULT_VERSION="v%s"' % new)],
    }
    for name, subs in edits.items():
        text = read(name)
        for pattern, repl in subs:
            text = re.sub(pattern, repl, text, flags=re.MULTILINE)
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        print("  bumped %s" % name)


def main(argv):
    if len(argv) == 3 and argv[1] == "--bump":
        bump(argv[2])
        argv = argv[:1]
    tag = argv[1] if len(argv) > 1 else None
    found = versions()
    problems = []
    for where, value in found.items():
        print("  %-24s %s" % (where, value))
        if value is None:
            problems.append("could not read the version from %s" % where)
    distinct = {v for v in found.values() if v is not None}
    if len(distinct) > 1:
        problems.append("versions disagree: %s" % ", ".join(sorted(distinct)))
    if tag is not None:
        want = tag[1:] if tag.startswith("v") else tag
        if distinct != {want}:
            problems.append("tag %s does not match the version in the files (%s)" % (tag, ", ".join(sorted(distinct))))
    problems += ["manifest.json: " + e for e in manifest_errors()]
    for problem in problems:
        print("ERROR: " + problem, file=sys.stderr)
    if not problems:
        print("ok: versions agree%s; manifest.json is a valid Omarchy plugin manifest" % (" with " + tag if tag else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
