#!/usr/bin/env python3
"""Install Context Colors into a copy of the currently selected Herdr layout."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


MODS = ("context-agents", "context-tabs")


def with_context(layout):
    result = deepcopy(layout)
    found = set()

    def visit(node):
        if isinstance(node, dict):
            content = node.get("content")
            if isinstance(content, dict) and content.get("mod") in ("agents", "tabs"):
                original = content["mod"]
                content["mod"] = "context-" + original
                found.add(original)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(result)
    if found != {"agents", "tabs"}:
        raise ValueError("The selected layout needs the standard agents and tabs mods. Select a compatible layout first.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-home", type=Path, default=Path.home() / ".config/herdr-app")
    parser.add_argument("--name", help="Name for the new layout (default: current layout + -context)")
    args = parser.parse_args()
    app = shutil.which("herdr-app") or str(Path.home() / ".local/bin/herdr-app")
    source = Path(__file__).resolve().parent

    def call(*arguments):
        return subprocess.check_output([app, *arguments], text=True, env={**os.environ, "HERDR_APP_HOME": str(args.app_home)})

    current = json.loads(call("status"))["layout"]
    name = args.name or current + "-context"
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ValueError("Use letters, digits, hyphens, or underscores for the layout name.")
    target_layout = args.app_home / "layouts" / (name + ".json")
    if target_layout.exists() or any((args.app_home / "mods" / name).exists() for name in MODS):
        raise FileExistsError("Context Colors already exists, or a name is taken. No installed files were changed.")
    # Validate compatibility before creating anything. The actual clone includes
    # the person's current layout clicks (widths, visibility, theme, etc.).
    with_context(json.loads((args.app_home / "layouts" / (current + ".json")).read_text()))
    for mod in MODS:
        call("check", str(source / "mods" / mod))
    for mod in MODS:
        shutil.copytree(source / "mods" / mod, args.app_home / "mods" / mod,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "gpui-kit.d.ts", "jsconfig.json", "*.error"))
        # Preserve the original status timestamps and panel preferences so
        # adding annotations does not change the person's existing ordering.
        previous = args.app_home / "data" / mod.removeprefix("context-") / "store.json"
        destination = args.app_home / "data" / mod / "store.json"
        if previous.exists() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(previous, destination)
            destination.chmod(0o600)
    try:
        call("do", "layout.clone", json.dumps({"name": current, "as": name}))
        original = target_layout.read_text()
        layout = with_context(json.loads(original))
        layout["preview"] = "layouts/" + name + ".svg"
        temporary = target_layout.with_suffix(".json.context-tmp")
        temporary.write_text(json.dumps(layout, indent=2) + "\n")
        if target_layout.read_text() != original:
            raise RuntimeError("The cloned layout changed during installation; refusing to overwrite it.")
        temporary.replace(target_layout)
        shutil.copyfile(source / "preview.svg", target_layout.with_suffix(".svg"))
        for mod in MODS:
            call("check", str(args.app_home / "mods" / mod))
        (args.app_home / ".context-colors-install.json").write_text(json.dumps({"original": current, "layout": name, "source": str(source)}, indent=2) + "\n")
    except Exception:
        call("do", "layout.switch", json.dumps({"name": current}))
        raise
    print(f"Context Colors installed in layout {name}. Previous layout: {current}.")
    print(f'To switch back: herdr-app do layout.switch \'{{"name":"{current}"}}\'')


if __name__ == "__main__":
    main()
