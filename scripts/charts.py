#!/usr/bin/env python3
"""Generate outreach dashboard charts from analyze.py metrics.

Usage:
    uv run python scripts/charts.py          # generate all charts
    uv run python scripts/charts.py --embed  # also print markdown image refs
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Insert parent so we can import analyze
sys.path.insert(0, str(Path(__file__).parent))
from analyze import compute_metrics, load_contacts, validate_contact_types

CHARTS_DIR = Path(__file__).parent.parent / "reports" / "charts"

# --- Style ---
COLORS = {
    "primary": "#2563eb",
    "secondary": "#64748b",
    "accent": "#f59e0b",
    "positive": "#10b981",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
    "bg": "#ffffff",
    "grid": "#e2e8f0",
}

STATUS_COLORS = {
    "mou_signed": "#7c3aed",
    "meeting_scheduled": "#2563eb",
    "met": "#0891b2",
    "replied": "#10b981",
    "declined": "#ef4444",
    "accepted": "#f59e0b",
    "sent": "#94a3b8",
    "draft": "#cbd5e1",
    "skipped": "#e2e8f0",
}

AUDIENCE_COLORS = [
    "#7c3aed", "#2563eb", "#0891b2", "#10b981",
    "#f59e0b", "#ef4444", "#64748b",
]


def setup_style():
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["bg"],
        "axes.edgecolor": COLORS["grid"],
        "axes.grid": True,
        "grid.color": COLORS["grid"],
        "grid.alpha": 0.5,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Apple SD Gothic Neo", "Arial"],
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.3,
    })


def chart_status_distribution(m: dict) -> Path:
    """Horizontal bar chart of status counts."""
    order = [
        "mou_signed", "meeting_scheduled", "met", "replied",
        "declined", "accepted", "sent", "draft", "skipped",
    ]
    labels = []
    values = []
    colors = []
    for s in order:
        if s in m["by_status"]:
            labels.append(s.replace("_", " "))
            values.append(m["by_status"][s])
            colors.append(STATUS_COLORS.get(s, COLORS["neutral"]))

    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, height=0.6, edgecolor="white", linewidth=0.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=10, fontweight="bold",
                color=COLORS["secondary"])

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_title(f"Status Distribution — {m['total']} contacts")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="y", visible=False)

    path = CHARTS_DIR / "status_distribution.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_engagement_rates_by_audience(m: dict) -> Path:
    """Grouped bar chart: cold-only vs overall engaged rate by audience."""
    audiences = list(m["by_audience"].keys())
    overall_rates = []
    cold_rates = []
    overall_labels = []
    cold_labels = []

    for at in audiences:
        d = m["by_audience"][at]
        act, eng = d["active"], d["engaged"]
        overall_rates.append((eng / act * 100) if act else 0)
        overall_labels.append(f"{eng}/{act}")
        ca, ce = d.get("cold_active", 0), d.get("cold_engaged", 0)
        cold_rates.append((ce / ca * 100) if ca else 0)
        cold_labels.append(f"{ce}/{ca}" if ca else "—")

    # Sort by cold rate descending (honest signal)
    order = sorted(range(len(audiences)), key=lambda i: cold_rates[i], reverse=True)
    audiences = [audiences[i] for i in order]
    overall_rates = [overall_rates[i] for i in order]
    cold_rates = [cold_rates[i] for i in order]
    overall_labels = [overall_labels[i] for i in order]
    cold_labels = [cold_labels[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(audiences))
    w = 0.3

    bars_c = ax.bar(x - w / 2, cold_rates, w, color="#64748b", edgecolor="white",
                    linewidth=0.5, label="Cold-only")
    bars_o = ax.bar(x + w / 2, overall_rates, w, color=COLORS["primary"], edgecolor="white",
                    linewidth=0.5, label="Overall")

    for bar, rate, lbl in zip(bars_c, cold_rates, cold_labels):
        if lbl != "—":
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%\n({lbl})", ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color="#64748b")
    for bar, rate, lbl in zip(bars_o, overall_rates, overall_labels):
        if rate > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%\n({lbl})", ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color=COLORS["primary"])

    ax.set_xticks(x)
    ax.set_xticklabels(audiences, rotation=25, ha="right")
    ax.set_ylabel("Engaged Rate (%)")
    ax.set_title("Engagement Rate by Audience Type (cold-only vs overall)")
    all_rates = overall_rates + cold_rates
    ax.set_ylim(0, max(all_rates) * 1.35 if all_rates else 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax.grid(axis="x", visible=False)

    path = CHARTS_DIR / "engagement_by_audience.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_channel_comparison(m: dict) -> Path:
    """Bar chart comparing channels with cold-only rate overlay."""
    channels = list(m["by_channel"].keys())
    overall_rates = []
    cold_rates = []
    labels = []

    for ch in channels:
        d = m["by_channel"][ch]
        active = d["active"]
        engaged = d["engaged"]
        rate = (engaged / active * 100) if active else 0
        cold_active = d["cold_active"]
        cold_engaged = d["cold_engaged"]
        c_rate = (cold_engaged / cold_active * 100) if cold_active else None
        overall_rates.append(rate)
        cold_rates.append(c_rate)
        labels.append(f"{ch}\n({d['active']} active)")

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(channels))
    width = 0.3

    bars1 = ax.bar(x - width / 2, overall_rates, width, color=COLORS["primary"],
                   edgecolor="white", linewidth=0.5, label="Overall rate")

    cold_vals = [r if r is not None else 0 for r in cold_rates]
    cold_mask = [r is not None for r in cold_rates]
    cold_colors = [COLORS["accent"] if has_cold else "none" for has_cold in cold_mask]
    cold_edges = [COLORS["accent"] if has_cold else "none" for has_cold in cold_mask]

    bars2 = ax.bar(x + width / 2, cold_vals, width, color=cold_colors,
                   edgecolor=cold_edges, linewidth=0.5, label="Cold-only rate")

    for bar, rate in zip(bars1, overall_rates):
        if rate > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%", ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color=COLORS["primary"])

    for bar, rate, show in zip(bars2, cold_rates, cold_mask):
        if show and rate and rate > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%", ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color=COLORS["accent"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Engaged Rate (%)")
    ax.set_title("Engagement Rate by Channel")
    ax.set_ylim(0, max(overall_rates) * 1.3 if overall_rates else 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="upper center", framealpha=0.9, fontsize=9)
    ax.grid(axis="x", visible=False)

    path = CHARTS_DIR / "engagement_by_channel.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_contact_type_breakdown(m: dict) -> Path:
    """Donut chart of contact type distribution + engagement."""
    types = list(m["by_contact_type"].keys())
    actives = [m["by_contact_type"][t]["active"] for t in types]
    engageds = [m["by_contact_type"][t]["engaged"] for t in types]
    rates = [
        f"{(e / a * 100):.0f}%" if a else "0%"
        for e, a in zip(engageds, actives)
    ]

    type_colors = ["#64748b", "#f59e0b", "#2563eb", "#10b981"]
    colors = type_colors[: len(types)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5.5),
                                    gridspec_kw={"width_ratios": [1, 1.2]})

    fig.suptitle("Cold vs Warm vs Referral vs Inbound",
                 fontsize=13, fontweight="bold")

    # Donut: active contacts by type
    wedges, texts, autotexts = ax1.pie(
        actives, labels=types, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(10)
        t.set_fontweight("bold")
    ax1.set_title("Active Contacts by Type", pad=12)

    # Bar: engaged rate by type
    x = np.arange(len(types))
    rate_vals = [(e / a * 100) if a else 0 for e, a in zip(engageds, actives)]
    bars = ax2.bar(x, rate_vals, color=colors, width=0.5, edgecolor="white", linewidth=0.5)
    for bar, rate, eng, act in zip(bars, rate_vals, engageds, actives):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f"{rate:.0f}%\n({eng}/{act})", ha="center", va="bottom",
                 fontsize=9, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(types)
    ax2.set_ylabel("Engaged Rate (%)")
    ax2.set_title("Engaged Rate by Contact Type", pad=12)
    ax2.set_ylim(0, max(rate_vals) * 1.35 if rate_vals else 100)
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax2.grid(axis="x", visible=False)

    fig.tight_layout(rect=[0, 0, 1, 0.95])

    path = CHARTS_DIR / "contact_type_breakdown.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_engagement_by_vertical(m: dict) -> Path:
    """Horizontal grouped bar: cold-only vs overall by vertical."""
    verticals = list(m["by_vertical"].keys())
    cold_rates = []
    overall_rates = []
    cold_lbl = []
    overall_lbl = []

    for v in verticals:
        d = m["by_vertical"][v]
        act, eng = d["active"], d["engaged"]
        overall_rates.append((eng / act * 100) if act else 0)
        overall_lbl.append(f"{eng}/{act}")
        ca, ce = d.get("cold_active", 0), d.get("cold_engaged", 0)
        cold_rates.append((ce / ca * 100) if ca else 0)
        cold_lbl.append(f"{ce}/{ca}" if ca else "—")

    # Sort by cold rate descending
    order = sorted(range(len(verticals)), key=lambda i: cold_rates[i], reverse=True)
    verticals = [verticals[i] for i in order]
    cold_rates = [cold_rates[i] for i in order]
    overall_rates = [overall_rates[i] for i in order]
    cold_lbl = [cold_lbl[i] for i in order]
    overall_lbl = [overall_lbl[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(verticals))
    h = 0.3

    bars_c = ax.barh(y + h / 2, cold_rates, h, color="#64748b", edgecolor="white",
                     linewidth=0.5, label="Cold-only")
    bars_o = ax.barh(y - h / 2, overall_rates, h, color=COLORS["primary"], edgecolor="white",
                     linewidth=0.5, label="Overall")

    for bar, rate, lbl in zip(bars_c, cold_rates, cold_lbl):
        if lbl != "—":
            ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                    f"{rate:.0f}% ({lbl})", va="center", fontsize=8,
                    fontweight="bold", color="#64748b")
    for bar, rate, lbl in zip(bars_o, overall_rates, overall_lbl):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{rate:.0f}% ({lbl})", va="center", fontsize=8,
                fontweight="bold", color=COLORS["primary"])

    ax.set_yticks(y)
    ax.set_yticklabels(verticals)
    ax.invert_yaxis()
    ax.set_xlabel("Engaged Rate (%)")
    ax.set_title("Engagement Rate by Vertical (cold-only vs overall)")
    all_r = cold_rates + overall_rates
    ax.set_xlim(0, max(all_r) * 1.45 if all_r else 100)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
    ax.grid(axis="y", visible=False)

    path = CHARTS_DIR / "engagement_by_vertical.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_period_comparison(m: dict) -> Path:
    """Grouped bar of old vs new batch: cold-only vs overall."""
    bp = m["by_period"]
    periods = ["Old batch\n(<Mar 4)", "New batch\n(>=Mar 4)", "Overall"]
    batches = [bp["old_batch"], bp["new_batch"], bp["overall"]]

    cold_rates = []
    overall_rates = []
    cold_lbl = []
    overall_lbl = []

    for b in batches:
        cc = b.get("cold_count", b.get("cold_active", 0))
        ce = b.get("cold_engaged", 0)
        tc = b.get("count", b.get("active", 0))
        te = b.get("engaged", 0)
        cold_rates.append((ce / cc * 100) if cc else 0)
        cold_lbl.append(f"{ce}/{cc}" if cc else "—")
        overall_rates.append((te / tc * 100) if tc else 0)
        overall_lbl.append(f"{te}/{tc}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(periods))
    w = 0.28

    bars_c = ax.bar(x - w / 2, cold_rates, w, color="#64748b", edgecolor="white",
                    linewidth=0.5, label="Cold-only")
    bars_o = ax.bar(x + w / 2, overall_rates, w, color=COLORS["primary"], edgecolor="white",
                    linewidth=0.5, label="Overall")

    for bar, rate, lbl in zip(bars_c, cold_rates, cold_lbl):
        if lbl != "—":
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{rate:.0f}%\n({lbl})", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color="#64748b")
    for bar, rate, lbl in zip(bars_o, overall_rates, overall_lbl):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{rate:.0f}%\n({lbl})", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color=COLORS["primary"])

    ax.set_xticks(x)
    ax.set_xticklabels(periods)
    ax.set_ylabel("Engaged Rate (%)")
    ax.set_title("Engagement by Period (cold-only vs overall)")
    all_r = cold_rates + overall_rates
    ax.set_ylim(0, max(all_r) * 1.4 if all_r else 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax.grid(axis="x", visible=False)

    path = CHARTS_DIR / "period_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_all(metrics: dict) -> list[Path]:
    """Generate all charts and return list of paths."""
    setup_style()
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    paths = [
        chart_status_distribution(metrics),
        chart_engagement_by_vertical(metrics),
        chart_channel_comparison(metrics),
        chart_contact_type_breakdown(metrics),
        chart_period_comparison(metrics),
    ]
    return paths


def main():
    parser = argparse.ArgumentParser(description="Generate outreach dashboard charts")
    parser.add_argument("--embed", action="store_true", help="Print markdown image refs")
    args = parser.parse_args()

    contacts = load_contacts()
    validate_contact_types(contacts)
    metrics = compute_metrics(contacts)

    paths = generate_all(metrics)

    for p in paths:
        print(f"  {p.relative_to(Path(__file__).parent.parent)}")

    if args.embed:
        print("\n--- Markdown embeds ---")
        for p in paths:
            rel = p.relative_to(Path(__file__).parent.parent / "reports")
            print(f"![{p.stem}]({rel})")

    print(f"\n{len(paths)} charts generated.")


if __name__ == "__main__":
    main()
