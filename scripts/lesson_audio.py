#!/usr/bin/env python3
"""Render a supplied short lesson script, without a model or learner-state writes.

Replaces ad hoc calls into the memo library. Local output is the default;
--publish explicitly puts only the immutable clip on main, without RSS or push.
The caller owns the script and final clip. Temporary synthesis belongs here.
"""
import argparse
import asyncio
import sys
import tempfile
from pathlib import Path
from subprocess import run

from memo import render_memo
from publish import commit_and_push, current_branch, jsdelivr_url, load_env

BASE = Path(__file__).resolve().parent.parent


def check_publication(output: Path):
    """Reject unsafe publication before paying for synthesis.

    The shared publisher commits the whole index; explicit path staging alone
    does not protect an unrelated change already staged by the user.
    """
    if not output.is_relative_to(BASE / "published_audio"):
        raise ValueError("--publish requires output inside published_audio")
    if current_branch() != "main":
        raise ValueError("--publish requires the main branch (not detached HEAD)")
    staged = run(["git", "diff", "--cached", "--name-only"], cwd=BASE,
                 capture_output=True, text=True, encoding="utf-8", check=True)
    if staged.stdout.strip():
        raise ValueError("--publish requires an empty index; preserve staged work first")
    ahead = run(["git", "rev-list", "origin/main..HEAD"], cwd=BASE,
                capture_output=True, text=True, encoding="utf-8", check=True)
    if ahead.stdout.strip():
        raise ValueError("--publish refuses unpushed commits; publish that work separately")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="UTF-8 text to speak")
    parser.add_argument("--output", required=True, type=Path, help="new .mp3 path")
    parser.add_argument("--publish", action="store_true", help="commit and push clip only")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    try:
        script = args.script.read_text(encoding="utf-8-sig").strip()
        if not script:
            raise ValueError("script is empty")
        if output.suffix.lower() != ".mp3":
            raise ValueError("output must end in .mp3")
        if args.output.is_symlink() or output.exists():
            raise ValueError(f"output already exists; use a new name: {output}")
        if args.publish:
            check_publication(output)
        load_env(BASE / ".env")
        with tempfile.TemporaryDirectory(prefix="lesson-audio-") as scratch:
            rendered = Path(scratch) / "clip.mp3"
            asyncio.run(render_memo(script, rendered))
            if not rendered.is_file() or rendered.stat().st_size == 0:
                raise RuntimeError("synthesis produced no nonempty audio file")
            output.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation protects a clip created during synthesis, too.
            with output.open("xb") as target:
                target.write(rendered.read_bytes())
        if args.publish:
            # A render can take time; check the branch/index again before commit.
            check_publication(output)
            result = commit_and_push([output], f"Lesson audio: {output.stem}")
            if result is False:
                raise RuntimeError("publication did not succeed")
        print(f"Local audio: {output}")
        if args.publish:
            print(f"Published URL: {jsdelivr_url(output)}")
        return 0
    except Exception as exc:
        print(f"lesson_audio: {exc}", file=sys.stderr)
        if output.is_file():
            print(f"Local file retained: {output}; delivery not confirmed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
