#!/usr/bin/env python3
"""Pre-tool-use lint dispatcher.

Hook entry point invoked by Claude Code before Write/Edit/MultiEdit and
Gmail MCP create_draft calls. Reads the tool input from stdin as JSON,
runs each rule, and exits with code 2 + stderr message if any rule
flags a BLOCK violation. WARN violations print but exit 0.

Usage (from Claude Code hook):
    uv run python scripts/lint/run_lint.py

The hook payload looks like:
    {
      "tool_name": "Write",
      "tool_input": {"file_path": "...", "content": "..."}
    }

Manual sweep mode:
    uv run python scripts/lint/run_lint.py --all

Scans every .md file in cold_contacts/, vendors/, drafts/, pitch_events/
plus reports/OUTREACH_REPORT.md, synthesizes a Write payload per file,
and reports all violations. Use before report regens to catch drift
from terminal/external edits that bypassed the PreToolUse hook.
"""
import json
import sys
from pathlib import Path

# Ensure scripts/ is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lint.rules import (  # noqa: E402
    body_headings,
    bom_leak,
    connection_note_length,
    drafts_in_omc,
    em_dash,
    email_domain_leak,
    frontmatter_schema,
    in_house_abbrev,
    language_signoff,
    linkedin_ui_artifacts,
    link_prefix_https,
    no_markdown_in_body,
    one_file_per_entity,
    outbound_draft_channel_mismatch,
    timezone_conversion,
    vc_nda,
)

RULES = [
    em_dash,
    linkedin_ui_artifacts,
    one_file_per_entity,
    frontmatter_schema,
    connection_note_length,
    email_domain_leak,
    bom_leak,
    vc_nda,
    link_prefix_https,
    language_signoff,
    drafts_in_omc,
    body_headings,
    no_markdown_in_body,
    timezone_conversion,
    outbound_draft_channel_mismatch,
    in_house_abbrev,
]

SWEEP_DIRS = ("cold_contacts", "vendors", "drafts", "pitch_events")
SWEEP_EXTRA_FILES = ("reports/OUTREACH_REPORT.md",)


def _run_all(tool_name: str, tool_input: dict) -> list:
    all_violations = []
    for rule in RULES:
        try:
            violations = rule.check(tool_name, tool_input)
            if violations:
                all_violations.extend(violations)
        except Exception as exc:
            print(f"[lint-error] rule {rule.__name__} raised: {exc}", file=sys.stderr)
    return all_violations


def _print_violations(violations: list) -> int:
    blocks = [v for v in violations if v.severity == "block"]
    warns = [v for v in violations if v.severity == "warn"]

    if blocks:
        print("LINT BLOCKED:", file=sys.stderr)
        for v in blocks:
            print(f"  [{v.rule}] {v.message}", file=sys.stderr)
    if warns:
        header = "LINT WARNINGS (non-blocking):" if not blocks else "Also warnings:"
        print(header, file=sys.stderr)
        for v in warns:
            print(f"  [{v.rule}] {v.message}", file=sys.stderr)

    return 2 if blocks else 0


def _sweep_mode() -> int:
    files: list[Path] = []
    for d in SWEEP_DIRS:
        dir_path = PROJECT_ROOT / d
        if dir_path.is_dir():
            files.extend(sorted(dir_path.rglob("*.md")))
    for extra in SWEEP_EXTRA_FILES:
        p = PROJECT_ROOT / extra
        if p.is_file():
            files.append(p)

    all_violations = []
    for f in files:
        try:
            content = f.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[sweep-skip] {f.relative_to(PROJECT_ROOT)}: {exc}", file=sys.stderr)
            continue
        payload = {"file_path": str(f), "content": content}
        violations = _run_all("Write", payload)
        all_violations.extend(violations)

    print(f"Scanned {len(files)} files.", file=sys.stderr)
    blocks = sum(1 for v in all_violations if v.severity == "block")
    warns = sum(1 for v in all_violations if v.severity == "warn")
    print(f"Found {blocks} block(s), {warns} warning(s).", file=sys.stderr)
    return _print_violations(all_violations)


def _hook_mode() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return 0  # Malformed stdin; do not block

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    return _print_violations(_run_all(tool_name, tool_input))


def main() -> None:
    if "--all" in sys.argv[1:]:
        sys.exit(_sweep_mode())
    sys.exit(_hook_mode())


if __name__ == "__main__":
    main()
