#!/usr/bin/env python3
"""Collect actual paired scores; no Elo or TCEC scaling extrapolation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import html
import json
from pathlib import Path

try:
    from .ledger import CampaignResults, read_journal, digest
except ImportError:
    from ledger import CampaignResults, read_journal, digest


def collect(rows, campaign, *, expected_pairs=None, profile=None):
    results = CampaignResults.replay(campaign, rows)
    pairs = [pair for pair in results.pairs() if profile is None or pair["profile"] == profile]
    if expected_pairs is not None and len(expected_pairs) != len(set(expected_pairs)):
        raise ValueError("duplicate expected pair identity")
    expected = None if expected_pairs is None else set(expected_pairs)
    if expected is not None:
        unexpected = {pair["pair"] for pair in pairs} - expected
        # A campaign can contain multiple stages; exclude their results, never
        # relabel them as results of this frozen stage.
        pairs = [pair for pair in pairs if pair["pair"] in expected]
    else:
        unexpected = set()
    table = defaultdict(lambda: {"points": 0.0, "games": 0, "pairs": 0, "W": 0, "D": 0, "L": 0})
    head = defaultdict(float)
    for pair in pairs:
        a, b, score = pair["first_player"], pair["second_player"], pair["score"]
        table[a]["points"] += score
        table[b]["points"] += 2 - score
        table[a]["pairs"] += 1
        table[b]["pairs"] += 1
        table[a]["games"] += 2
        table[b]["games"] += 2
        head[a, b] += score
        head[b, a] += 2 - score
    complete_ids = {pair["pair"] for pair in pairs}
    raw_games, incomplete_games = [], []
    for state in results.games.values():
        if profile is not None and state.spec["profile"] != profile:
            continue
        if expected is not None and state.pair not in expected:
            continue
        if state.accepted:
            raw_games.append({"game": state.game, "pair": state.pair, "attempt": state.attempt,
                              "white": state.spec["white"], "black": state.spec["black"],
                              "result": state.result["result"], "reason": state.result["reason"],
                              "complete_pair": state.pair in complete_ids})
            if state.pair in complete_ids:
                result = state.result["result"]
                if result == "1/2-1/2":
                    table[state.spec["white"]]["D"] += 1
                    table[state.spec["black"]]["D"] += 1
                else:
                    winner, loser = ((state.spec["white"], state.spec["black"]) if result == "1-0" else
                                     (state.spec["black"], state.spec["white"]))
                    table[winner]["W"] += 1
                    table[loser]["L"] += 1
        else:
            incomplete_games.append({"game": state.game, "pair": state.pair, "attempt": state.attempt,
                                     "reason": state.interrupted or "result/remote acknowledgement pending"})
    standings = []
    for player, score in table.items():
        tied = {name for name, other in table.items() if other["points"] == score["points"]}
        h2h = sum(head[player, name] for name in tied if name != player)
        sb = sum(head[player, name] * other["points"] for name, other in table.items() if name != player)
        standings.append({"player": player, **score, "tied_head_to_head": h2h, "sonneborn_berger": sb})
    standings.sort(key=lambda row: (-row["points"], -row["tied_head_to_head"], -row["sonneborn_berger"], row["player"]))
    complete = bool(expected) and complete_ids == expected
    return {"format": "rove4k-paired-summary-v1", "campaign": campaign, "profile": profile,
            "completed_pairs": pairs, "completed_pair_count": len(pairs),
            "expected_pair_count": None if expected is None else len(expected),
            "missing_pairs": [] if expected is None else sorted(expected - complete_ids),
            "other_stage_pairs_excluded": sorted(unexpected), "campaign_stage_complete": complete,
            "standings": standings, "raw_completed_games": raw_games, "incomplete_attempts": incomplete_games,
            "selection_ready": complete,
            "scope": "complete colour pairs at one TEST resource profile; partials preserved; no Elo, equivalence or W256 claim"}


def select_high(summary, broad_families, high_players):
    """Choose up to two distinct eligible Rove families from completed broad."""
    if summary.get("profile") != "test-p4" or summary.get("selection_ready") is not True:
        raise ValueError("an incomplete broad stage cannot determine its top two")
    if len({row["family"] for row in high_players}) != len(high_players):
        raise ValueError("P28 selection requires one qualified artifact per family")
    eligible = {row["family"]: row["id"] for row in high_players if row["family"] in tuple("ABCDEF")}
    selected, families = [], set()
    for standing in summary["standings"]:
        family = broad_families[standing["player"]]
        if family in eligible and family not in families:
            selected.append(eligible[family])
            families.add(family)
            if len(families) == 2:
                break
    selected += sorted(row["id"] for row in high_players if row["family"] in ("ice4", "c4ke"))
    return {"players": selected, "rove_families": sorted(families),
            "partial": len(families) < 2 or sum(row["family"] in ("ice4", "c4ke") for row in high_players) < 2,
            "selection": "complete P4 pair points, tied head-to-head, Sonneborn-Berger, stable ID; among P28-qualified families"}


def write_summary(summary, out):
    out = Path(out)
    if not out.is_absolute() or out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("new absolute external collection directory required")
    out.mkdir(parents=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    columns = ("player", "points", "games", "pairs", "W", "D", "L", "tied_head_to_head", "sonneborn_berger")
    with (out / "standings.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(summary["standings"])
    rows = summary["standings"]
    height = 100 + len(rows) * 34
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="780" height="{height}" viewBox="0 0 780 {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="20" y="25" font-size="16">Observed complete-pair W / D / L counts</text>']
    maximum = max((row["games"] for row in rows), default=1)
    for index, row in enumerate(rows):
        y, x = 48 + index * 34, 170
        svg.append(f'<text x="20" y="{y+17}" font-size="13">{html.escape(row["player"])}</text>')
        for key, color in (("W", "#327d5f"), ("D", "#aeb8c3"), ("L", "#be5b52")):
            width = row[key] / maximum * 480
            svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="23" fill="{color}"/>')
            x += width
        svg.append(f'<text x="670" y="{y+17}" font-size="12">{row["W"]}/{row["D"]}/{row["L"]}</text>')
    svg.append(f'<text x="20" y="{height-12}" font-size="11">No Elo or cross-resource scaling inference; incomplete pairs are excluded.</text></svg>')
    (out / "scores.svg").write_text("\n".join(svg))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--profile", choices=("test-p4", "test-p28"))
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    expected = None
    if args.plan:
        value = json.loads(args.plan.read_text())
        if (value.get("format") != "rove4k-campaign-plan-v1" or
                digest(value.get("content")) != value.get("sha256") or
                value["content"].get("campaign") != args.campaign or
                args.profile is not None and value["content"].get("profile") != args.profile):
            parser.error("frozen plan identity/campaign/profile differs")
        args.profile = value["content"]["profile"]
        expected = [row["id"] for row in value["content"]["pairs"]]
    summary = collect(read_journal(args.journal, args.campaign), args.campaign,
                      expected_pairs=expected, profile=args.profile)
    write_summary(summary, args.out)
    print(json.dumps({"completed_pairs": summary["completed_pair_count"], "stage_complete": summary["campaign_stage_complete"]}))


if __name__ == "__main__":
    main()
