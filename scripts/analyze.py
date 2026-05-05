#!/usr/bin/env python3
"""Analyze cold_contacts.yml and print outreach metrics.

Usage:
    uv run python scripts/analyze.py          # text report (default)
    uv run python scripts/analyze.py --json   # structured JSON output
"""

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import yaml

# Make scripts/ importable so analyze.py can read the shared lint config.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint._config import PRIMARY_ENTITY  # noqa: E402

DB_PATH = Path(__file__).parent.parent / "cold_contacts.yml"

# Statuses that count as "engaged" (replied or better)
ENGAGED = {"replied", "declined", "met", "mou_signed", "meeting_scheduled"}
ACCEPTED = {"accepted"}
POSITIVE = ENGAGED | ACCEPTED
VALID_CONTACT_TYPES = {"cold", "warm", "referral", "inbound"}


def load_contacts() -> list[dict]:
    with open(DB_PATH) as f:
        return yaml.safe_load(f)


def parse_date(val: str | None) -> date | None:
    if not val:
        return None
    s = str(val).strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return None


def validate_contact_types(contacts: list[dict]) -> None:
    """Validate that every contact has a valid contact_type tag."""
    errors = []
    for c in contacts:
        slug = c.get("slug", "???")
        ct = c.get("contact_type")
        if ct is None:
            errors.append(f"  MISSING contact_type: {slug}")
        elif ct not in VALID_CONTACT_TYPES:
            errors.append(f"  INVALID contact_type '{ct}': {slug}")
    if errors:
        print("=" * 60, file=sys.stderr)
        print("ERROR: contact_type validation failed", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n{len(errors)} contact(s) missing or invalid contact_type.", file=sys.stderr)
        print("Every contact must have contact_type: cold | warm | referral | inbound", file=sys.stderr)
        sys.exit(1)


def compute_metrics(contacts: list[dict]) -> dict:
    """Compute all metrics and return structured data."""
    total = len(contacts)
    primary = [c for c in contacts if c.get("related_to") == PRIMARY_ENTITY]
    personal = [c for c in contacts if c.get("related_to") != PRIMARY_ENTITY]

    status_counts = dict(Counter(c.get("status", "unknown") for c in contacts))
    active_primary = [c for c in primary if c.get("status") not in ("skipped", "draft", None)]
    active_count = len(active_primary)
    engaged = [c for c in primary if c.get("status") in ENGAGED]
    accepted_list = [c for c in primary if c.get("status") in ACCEPTED]
    positive_list = [c for c in primary if c.get("status") in POSITIVE]

    def rate(n, d):
        return round(n / d * 100, 1) if d else 0

    # By status with names
    by_status = {}
    for c in contacts:
        s = c.get("status", "unknown")
        by_status.setdefault(s, []).append(c["name"])


    # By channel (cold-only rate for honest signal)
    channels = sorted(set(c.get("channel", "unknown") for c in primary))
    by_channel = {}
    for ch in channels:
        pool = [c for c in primary if c.get("channel") == ch]
        active = [c for c in pool if c.get("status") not in ("skipped", "draft", None)]
        eng = [c for c in pool if c.get("status") in ENGAGED]
        acc = [c for c in pool if c.get("status") in ACCEPTED]
        cold_active = [c for c in active if c.get("contact_type") == "cold"]
        cold_eng = [c for c in cold_active if c.get("status") in ENGAGED]
        by_channel[ch] = {
            "total": len(pool), "active": len(active),
            "engaged": len(eng), "accepted": len(acc),
            "rate": f"{rate(len(eng), len(active))}%",
            "cold_active": len(cold_active), "cold_engaged": len(cold_eng),
            "cold_rate": f"{rate(len(cold_eng), len(cold_active))}%",
        }

    # By contact type
    contact_types = sorted(set(c.get("contact_type", "cold") for c in primary))
    by_contact_type = {}
    for ct in contact_types:
        pool = [c for c in primary if c.get("contact_type", "cold") == ct]
        active = [c for c in pool if c.get("status") not in ("skipped", "draft", None)]
        eng = [c for c in pool if c.get("status") in ENGAGED]
        acc = [c for c in pool if c.get("status") in ACCEPTED]
        by_contact_type[ct] = {
            "total": len(pool), "active": len(active),
            "engaged": len(eng), "accepted": len(acc),
            "rate": f"{rate(len(eng), len(active))}%",
            "engaged_names": [c["name"] for c in eng],
        }

    # By vertical (cold-only + overall)
    verticals = sorted(set(c.get("vertical", "other") for c in primary))
    by_vertical = {}
    for v in verticals:
        pool = [c for c in primary if c.get("vertical") == v]
        active = [c for c in pool if c.get("status") not in ("skipped", "draft", None)]
        eng = [c for c in pool if c.get("status") in ENGAGED]
        acc = [c for c in pool if c.get("status") in ACCEPTED]
        cold_active = [c for c in active if c.get("contact_type") == "cold"]
        cold_eng = [c for c in cold_active if c.get("status") in ENGAGED]
        by_vertical[v] = {
            "total": len(pool), "active": len(active),
            "engaged": len(eng), "accepted": len(acc),
            "rate": f"{rate(len(eng), len(active))}%",
            "cold_active": len(cold_active), "cold_engaged": len(cold_eng),
            "cold_rate": f"{rate(len(cold_eng), len(cold_active))}%",
            "engaged_names": [c["name"] for c in eng],
            "accepted_names": [c["name"] for c in acc],
        }

    # By period (with cold/warm splits)
    cutoff = date(2026, 3, 4)
    old_batch = [c for c in active_primary if (d := parse_date(c.get("sent_at"))) and d < cutoff]
    new_batch = [c for c in active_primary if (d := parse_date(c.get("sent_at"))) and d >= cutoff]
    no_date = [c for c in active_primary if not parse_date(c.get("sent_at"))]
    old_engaged = [c for c in old_batch if c.get("status") in ENGAGED]
    new_engaged = [c for c in new_batch if c.get("status") in ENGAGED]
    # Cold splits
    old_cold = [c for c in old_batch if c.get("contact_type") == "cold"]
    old_cold_eng = [c for c in old_cold if c.get("status") in ENGAGED]
    new_cold = [c for c in new_batch if c.get("contact_type") == "cold"]
    new_cold_eng = [c for c in new_cold if c.get("status") in ENGAGED]
    all_cold = [c for c in active_primary if c.get("contact_type") == "cold"]
    all_cold_eng = [c for c in all_cold if c.get("status") in ENGAGED]
    # Warm splits
    old_warm = [c for c in old_batch if c.get("contact_type") != "cold"]
    old_warm_eng = [c for c in old_warm if c.get("status") in ENGAGED]
    new_warm = [c for c in new_batch if c.get("contact_type") != "cold"]
    new_warm_eng = [c for c in new_warm if c.get("status") in ENGAGED]
    all_warm = [c for c in active_primary if c.get("contact_type") != "cold"]
    all_warm_eng = [c for c in all_warm if c.get("status") in ENGAGED]

    # Active conversations (replied/met/meeting_scheduled with recent activity)
    active_conversations = []
    for c in primary:
        if c.get("status") in (ENGAGED | ACCEPTED):
            last_event = (c.get("last_replied_at") or c.get("met_at") or
                          c.get("meeting_at") or c.get("accepted_at") or c.get("sent_at"))
            active_conversations.append({
                "slug": c["slug"], "name": c["name"],
                "company": c.get("company", ""),
                "status": c.get("status"),
                "last_event_date": str(last_event) if last_event else None,
                "notes": (c.get("notes") or "")[:200],
            })

    # Needs follow-up
    needs_followup = []
    today = date.today()
    for c in primary:
        if c.get("status") in ACCEPTED and not c.get("followed_up_at"):
            acc_date = parse_date(c.get("accepted_at"))
            days = (today - acc_date).days if acc_date else None
            needs_followup.append({
                "slug": c["slug"], "name": c["name"],
                "company": c.get("company", ""),
                "status": c.get("status"),
                "days_since_accept": days,
            })

    # Upcoming meetings
    upcoming_meetings = []
    for c in primary:
        if c.get("status") == "meeting_scheduled":
            upcoming_meetings.append({
                "slug": c["slug"], "name": c["name"],
                "company": c.get("company", ""),
                "meeting_at": str(c.get("meeting_at", "?")),
            })

    # Warnings (lint)
    warnings = []
    for c in contacts:
        slug = c.get("slug", "?")
        if c.get("status") == "meeting_scheduled" and not c.get("meeting_at"):
            warnings.append(f"{slug}: meeting_scheduled but meeting_at is null")
        if c.get("status") in {"replied", "met", "mou_signed"} and not c.get("last_replied_at"):
            warnings.append(f"{slug}: status={c['status']} but last_replied_at is null")

    return {
        "generated_at": str(date.today()),
        "total": total,
        "primary_count": len(primary),
        "personal_count": len(personal),
        "by_status": status_counts,
        "by_status_names": by_status,
        "engagement_rates": {
            "active": active_count,
            "engaged": len(engaged),
            "engaged_rate": f"{rate(len(engaged), active_count)}%",
            "accepted_connected": len(accepted_list),
            "positive": len(positive_list),
            "positive_rate": f"{rate(len(positive_list), active_count)}%",
        },
        "by_channel": by_channel,
        "by_contact_type": by_contact_type,
        "by_vertical": by_vertical,
        "by_period": {
            "old_batch": {"count": len(old_batch), "engaged": len(old_engaged),
                          "rate": f"{rate(len(old_engaged), len(old_batch))}%",
                          "cold_count": len(old_cold), "cold_engaged": len(old_cold_eng),
                          "cold_rate": f"{rate(len(old_cold_eng), len(old_cold))}%",
                          "warm_count": len(old_warm), "warm_engaged": len(old_warm_eng),
                          "warm_rate": f"{rate(len(old_warm_eng), len(old_warm))}%"},
            "new_batch": {"count": len(new_batch), "engaged": len(new_engaged),
                          "rate": f"{rate(len(new_engaged), len(new_batch))}%",
                          "cold_count": len(new_cold), "cold_engaged": len(new_cold_eng),
                          "cold_rate": f"{rate(len(new_cold_eng), len(new_cold))}%",
                          "warm_count": len(new_warm), "warm_engaged": len(new_warm_eng),
                          "warm_rate": f"{rate(len(new_warm_eng), len(new_warm))}%"},
            "no_date": len(no_date),
            "overall": {"active": active_count, "engaged": len(engaged),
                        "rate": f"{rate(len(engaged), active_count)}%",
                        "cold_active": len(all_cold), "cold_engaged": len(all_cold_eng),
                        "cold_rate": f"{rate(len(all_cold_eng), len(all_cold))}%",
                        "warm_active": len(all_warm), "warm_engaged": len(all_warm_eng),
                        "warm_rate": f"{rate(len(all_warm_eng), len(all_warm))}%"},
        },
        "active_conversations": active_conversations,
        "needs_followup": needs_followup,
        "upcoming_meetings": upcoming_meetings,
        "warnings": warnings,
    }


def print_text_report(m: dict) -> None:
    """Print human-readable text report from metrics dict."""
    print("=" * 60)
    print(f"OUTREACH METRICS — {m['generated_at']}")
    print("=" * 60)

    print(f"\nTotal contacts: {m['total']}")
    print(f"  {PRIMARY_ENTITY}-related: {m['primary_count']}")
    print(f"  personal network: {m['personal_count']}")
    print()

    print("STATUS DISTRIBUTION (all)")
    print("-" * 40)
    order = [
        "mou_signed", "meeting_scheduled", "met", "replied",
        "declined", "connected", "accepted", "sent", "draft", "skipped",
    ]
    for s in order:
        if s in m["by_status"]:
            names = m["by_status_names"].get(s, [])
            print(f"  {s:20s} {m['by_status'][s]:3d}  {', '.join(names)}")
    for s in sorted(set(m["by_status"]) - set(order)):
        print(f"  {s:20s} {m['by_status'][s]:3d}")
    print(f"  {'TOTAL':20s} {m['total']:3d}")

    er = m["engagement_rates"]
    print()
    print(f"ENGAGEMENT RATES ({PRIMARY_ENTITY}-related, excl. skipped/draft)")
    print("-" * 40)
    print(f"  Active contacts:    {er['active']}")
    print(f"  Engaged (replied+): {er['engaged']} ({er['engaged_rate']})")
    print(f"  Accepted/Connected: {er['accepted_connected']}")
    print(f"  Positive total:     {er['positive']} ({er['positive_rate']})")

    print()
    print("BY CHANNEL (cold-only rate in parentheses)")
    print("-" * 40)
    print(f"  {'Channel':20s} {'Total':>5s} {'Active':>6s} {'Engaged':>7s} {'Rate':>7s} {'Cold':>12s} {'Acc':>4s}")
    for ch, s in m["by_channel"].items():
        cold_str = f"{s['cold_engaged']}/{s['cold_active']} {s['cold_rate']}" if s["cold_active"] else "—"
        print(f"  {ch:20s} {s['total']:5d} {s['active']:6d} {s['engaged']:7d} {s['rate']:>7s} {cold_str:>12s} {s['accepted']:4d}")

    bp = m["by_period"]
    print()
    print("BY PERIOD")
    print("-" * 40)
    print(f"  Old batch (<Mar 4):  {bp['old_batch']['engaged']}/{bp['old_batch']['count']} ({bp['old_batch']['rate']})")
    print(f"  New batch (>=Mar 4): {bp['new_batch']['engaged']}/{bp['new_batch']['count']} ({bp['new_batch']['rate']})")
    if bp["no_date"]:
        print(f"  No sent_at date:     {bp['no_date']}")
    print(f"  Overall:             {bp['overall']['engaged']}/{bp['overall']['active']} ({bp['overall']['rate']})")

    print()
    print("BY CONTACT TYPE (cold/warm/referral/inbound)")
    print("-" * 40)
    print(f"  {'Type':12s} {'Total':>5s} {'Active':>6s} {'Engaged':>7s} {'Rate':>7s} {'Acc':>4s}")
    for ct, s in m["by_contact_type"].items():
        print(f"  {ct:12s} {s['total']:5d} {s['active']:6d} {s['engaged']:7d} {s['rate']:>7s} {s['accepted']:4d}")
        if s.get("engaged_names"):
            print(f"    engaged: {', '.join(s['engaged_names'])}")

    if m["needs_followup"]:
        print()
        print("NEEDS FOLLOW-UP (accepted/connected, no follow-up recorded)")
        print("-" * 40)
        for c in m["needs_followup"]:
            days = f" ({c['days_since_accept']}d ago)" if c["days_since_accept"] is not None else ""
            print(f"  {c['name']} ({c['company']}) — {c['status']}{days}")

    if m["upcoming_meetings"]:
        print()
        print("UPCOMING MEETINGS")
        print("-" * 40)
        for c in m["upcoming_meetings"]:
            print(f"  {c['name']} ({c['company']}) — {c['meeting_at']}")

    if m["warnings"]:
        print()
        print("WARNINGS")
        print("-" * 40)
        for w in m["warnings"]:
            print(f"  ⚠ {w}")


def main():
    parser = argparse.ArgumentParser(description="Analyze outreach contacts")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    contacts = load_contacts()
    validate_contact_types(contacts)
    metrics = compute_metrics(contacts)

    if args.json:
        # Remove by_status_names from JSON (verbose, text-report only)
        output = {k: v for k, v in metrics.items() if k != "by_status_names"}
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        print()  # trailing newline
    else:
        print_text_report(metrics)


if __name__ == "__main__":
    main()
