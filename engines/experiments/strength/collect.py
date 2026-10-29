#!/usr/bin/env python3
"""Collect actual paired scores; no Elo or TCEC scaling extrapolation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import html
import json
import math
from pathlib import Path

try:
    from .ledger import CampaignResults, read_journal, digest, cooperative_gc_scope_id, valid_boot_id, valid_id
except ImportError:
    from ledger import CampaignResults, read_journal, digest, cooperative_gc_scope_id, valid_boot_id, valid_id


def order_standings(standings, player_families=None):
    """Bind statistical ties to family IDs; unbound ID order is reporting only."""
    rows = list(standings)
    if player_families is not None and type(player_families) is not dict:
        raise ValueError("an artifact-to-family mapping is required")
    seen = set()
    for row in rows:
        player = row.get("player")
        if type(player) is not str or not player or player in seen:
            raise ValueError("unique standing player identities are required")
        seen.add(player)
        if player_families is not None and player_families.get(player) not in (*"ABCDEF", "ice4", "c4ke"):
            raise ValueError("standing has no declared active family")
        if any(type(row.get(name)) not in (int, float) or not math.isfinite(row[name])
               for name in ("points", "tied_head_to_head", "sonneborn_berger")):
            raise ValueError("finite point and tie-break observations are required")

    def key(row):
        player = row["player"]
        family = player if player_families is None else player_families[player]
        return (-row["points"], -row["tied_head_to_head"], -row["sonneborn_berger"], family, player)

    return sorted(rows, key=key)


def finite_monotonic(value):
    return (type(value) in (int, float) and 0 <= value <= ((1 << 63) - 1) / 1_000_000_000
            and math.isfinite(value))


def conservative_monotonic_ns(value, *, lower):
    """Bound float clock rounding outwards, without accepting an unobserved gap."""
    if not finite_monotonic(value):
        raise ValueError("finite monotonic time required")
    if type(value) is int:
        return value * 1_000_000_000
    neighbour = math.nextafter(value, -math.inf if lower else math.inf)
    numerator, denominator = neighbour.as_integer_ratio()
    scaled = numerator * 1_000_000_000
    return scaled // denominator if lower else -((-scaled) // denominator)


def cooperative_gc_status(rows, campaign, state):
    """Classify explicit GC by the owning controller, not Python's automatic GC.

    A missing, incomplete or inconsistent interval is not a clean interval.
    Journal records identify the declared owner; they are not host attestation.
    """
    indexed = [(index, row) for index, row in enumerate(rows)
               if row.get("campaign") == campaign and row.get("pair") == state.pair
               and row.get("game") == state.game and row.get("attempt") == state.attempt]
    if any(type(row.get("attempt")) is not int for _, row in indexed):
        return "unverified"
    def events(name):
        return [(index, row.get("data")) for index, row in indexed if row.get("event") == name]
    processes = events("game.process")
    completions = events("game.process_completed")
    opened = events("game.cooperative_gc_open")
    closed = events("game.cooperative_gc_close")
    result = events("game.result")
    if len(processes) != 1 or len(completions) != 1 or len(opened) != 1 or len(closed) != 1 or not result:
        return "unverified"
    process_index, process = processes[0]
    completed_index, completed = completions[0]
    open_index, start = opened[0]
    close_index, end = closed[0]
    if not (process_index < open_index < completed_index < result[0][0] < close_index):
        return "unverified"
    if any(type(value) is not dict for value in (process, completed, start, end)):
        return "unverified"
    for name in ("pid", "pgid", "session", "start_ticks"):
        if (type(process.get(name)) is not int or type(completed.get(name)) is not int or
                process[name] != completed[name]):
            return "unverified"
    if (process["pid"] <= 0 or process["pgid"] != process["pid"] or
            process["session"] != process["pid"] or process["start_ticks"] < 0 or
            type(process.get("identity")) is not str or not process["identity"] or
            completed.get("identity") != process["identity"] or
            completed.get("gate_released") is not True or
            completed.get("cleanup_forced") is not False or
            type(completed.get("returncode")) is not int or completed["returncode"] != 0 or
            completed.get("readers_done") is not True or completed.get("remaining_processes") != []):
        return "unverified"
    identity_names = {"instance_id", "boot_id", "launch_pid", "launch_start_ticks",
                      "observer_pid", "observer_start_ticks", "scope_start_ns"}
    common = identity_names | {"format", "coverage_scope", "scope_id", "request_count",
                               "performed_count", "active_count", "coverage_complete"}
    if set(start) != common or set(end) != common | {"scope_end_ns", "result_sha256"}:
        return "unverified"
    if any(type(start[name]) is not type(end[name]) or start[name] != end[name]
           for name in identity_names | {"format", "coverage_scope", "scope_id"}):
        return "unverified"
    if (start["format"] != "rove4k-cooperative-gc-v1" or
            start["coverage_scope"] != "owned-controller-explicit-gc" or
            start["coverage_complete"] is not True or end["coverage_complete"] is not True or
            end["result_sha256"] != state.result_sha256):
        return "unverified"
    identity = {name: start[name] for name in identity_names}
    try:
        expected = cooperative_gc_scope_id(campaign, state.pair, state.game, state.attempt, identity)
    except (TypeError, ValueError):
        return "unverified"
    if (start["scope_id"] != expected or type(process.get("pid")) is not int or
            type(process.get("start_ticks")) is not int or
            process.get("instance_id") != identity["instance_id"] or
            process.get("boot_id") != identity["boot_id"] or process.get("pid") != identity["launch_pid"] or
            process.get("start_ticks") != identity["launch_start_ticks"] or
            type(end["scope_end_ns"]) is not int or
            not identity["scope_start_ns"] <= end["scope_end_ns"] <= (1 << 63) - 1):
        return "unverified"
    spawned, finished = process.get("spawn_monotonic"), completed.get("completed_monotonic")
    if (not finite_monotonic(spawned) or not finite_monotonic(finished) or finished < spawned or
            identity["scope_start_ns"] > conservative_monotonic_ns(spawned, lower=True) or
            end["scope_end_ns"] < conservative_monotonic_ns(finished, lower=False)):
        return "unverified"
    for name in ("request_count", "performed_count"):
        if (type(start[name]) is not int or type(end[name]) is not int or
                not 0 <= start[name] <= end[name] <= (1 << 63) - 1):
            return "unverified"
    if any(type(value) is not int or not 0 <= value <= (1 << 63) - 1
           for value in (start["active_count"], end["active_count"])):
        return "unverified"
    if any(record["performed_count"] > record["request_count"] or
           record["active_count"] > record["request_count"] - record["performed_count"]
           for record in (start, end)):
        return "unverified"
    if (start["active_count"] or end["active_count"] or
            any(end[name] != start[name] for name in ("request_count", "performed_count"))):
        return "intervened"
    return "clean"


def reconcile_cooperative_gc_scopes(rows, campaign, results, accepted, statuses):
    """Reject contradictory concurrent scopes from the same controller or host.

    This only compares scopes present in this journal; it is not proof that
    every other process on a host is observed.
    """
    windows, unresolved = [], []
    for state in results.games.values():
        relevant = [(index, row) for index, row in enumerate(rows) if row.get("campaign") == campaign and
                    row.get("pair") == state.pair and row.get("game") == state.game and
                    row.get("attempt") == state.attempt]
        status = cooperative_gc_status(rows, campaign, state) if state.result is not None else "unverified"
        if status == "unverified":
            unresolved.append((state, relevant))
            continue
        open_index, opened = next((index, row) for index, row in relevant
                                  if row.get("event") == "game.cooperative_gc_open")
        close_index, closed = next((index, row) for index, row in relevant
                                   if row.get("event") == "game.cooperative_gc_close")
        start, end = opened["data"], closed["data"]
        windows.append({"game": state.game, "attempt": state.attempt, "start": start, "end": end,
                        "open_index": open_index, "close_index": close_index,
                        "host": (start["instance_id"], start["boot_id"]),
                        "observer": (start["observer_pid"], start["observer_start_ticks"])})
    def mark(window, value):
        state = accepted.get(window["game"])
        if state is not None and state.attempt == window["attempt"]:
            statuses[window["game"]] = value
    groups = defaultdict(list)
    for window in windows:
        groups[window["host"], window["observer"]].append(window)
    for group in groups.values():
        snapshots = []
        for window in group:
            for timestamp, row in ((window["start"]["scope_start_ns"], window["start"]),
                                   (window["end"]["scope_end_ns"], window["end"])):
                snapshots.append((timestamp, row["request_count"], row["performed_count"],
                                  row["active_count"]))
        snapshots.sort()
        if any((later[0] == earlier[0] and later[1:] != earlier[1:]) or
               later[1] < earlier[1] or later[2] < earlier[2]
               for earlier, later in zip(snapshots, snapshots[1:])):
            for window in group:
                mark(window, "unverified")
            continue
        for window in group:
            if any(active and window["start"]["scope_start_ns"] <= timestamp <= window["end"]["scope_end_ns"]
                   for timestamp, _, _, active in snapshots):
                mark(window, "intervened")
    for index, first in enumerate(windows):
        for second in windows[index + 1:]:
            if (first["host"] == second["host"] and first["observer"] != second["observer"] and
                    max(first["start"]["scope_start_ns"], second["start"]["scope_start_ns"]) <=
                    min(first["end"]["scope_end_ns"], second["end"]["scope_end_ns"])):
                mark(first, "unverified")
                mark(second, "unverified")
    for state, relevant in unresolved:
        processes = [row.get("data") for _, row in relevant if row.get("event") == "game.process"]
        completions = [row.get("data") for _, row in relevant if row.get("event") == "game.process_completed"]
        for window in windows:
            if len(processes) != 1 or type(processes[0]) is not dict:
                mark(window, "unverified")
                continue
            process = processes[0]
            instance, boot = process.get("instance_id"), process.get("boot_id")
            try:
                valid_id(instance)
            except ValueError:
                mark(window, "unverified")
                continue
            if not valid_boot_id(boot):
                mark(window, "unverified")
                continue
            if (instance, boot) != window["host"]:
                continue
            spawned = process.get("spawn_monotonic")
            if not finite_monotonic(spawned):
                mark(window, "unverified")
                continue
            finished = None
            if len(completions) == 1 and type(completions[0]) is dict:
                completion = completions[0]
                end_time = completion.get("completed_monotonic")
                identity = ("pid", "pgid", "session", "start_ticks")
                if (all(type(process.get(name)) is int and type(completion.get(name)) is int and
                        process[name] == completion[name] for name in identity) and
                        process["pid"] > 0 and process["pgid"] == process["pid"] and
                        process["session"] == process["pid"] and process["start_ticks"] >= 0 and
                        type(process.get("identity")) is str and process["identity"] and
                        completion.get("identity") == process["identity"] and
                        completion.get("readers_done") is True and completion.get("remaining_processes") == [] and
                        type(completion.get("returncode")) is int and finite_monotonic(end_time) and
                        end_time >= spawned):
                    finished = end_time
            possible_start = conservative_monotonic_ns(spawned, lower=True)
            possible_end = None if finished is None else conservative_monotonic_ns(finished, lower=False)
            if (possible_start <= window["end"]["scope_end_ns"] and
                    (possible_end is None or possible_end >= window["start"]["scope_start_ns"])):
                mark(window, "unverified")
    return statuses


def bind_plan_games(results, plan, campaign, profile, expected_pairs):
    """Check journal identities against the caller's frozen plan content.

    This checks consistency only. It does not authenticate the plan, journal,
    host, GO delivery or remote object acknowledgements.
    """
    if (type(plan) is not dict or plan.get("campaign") != campaign or
            plan.get("profile") != profile or type(plan.get("pairs")) is not list or
            type(plan.get("registry")) is not dict or
            type(plan["registry"].get("players")) is not list):
        raise ValueError("frozen plan does not match collection scope")
    players = {}
    for row in plan["registry"]["players"]:
        artifact = row.get("artifact") if type(row) is dict else None
        if type(artifact) is not dict:
            raise ValueError("frozen plan player is malformed")
        player, sha = artifact.get("id"), artifact.get("sha256")
        if (type(player) is not str or not player or player in players or
                type(sha) is not str or len(sha) != 64 or
                any(c not in "0123456789abcdef" for c in sha)):
            raise ValueError("frozen plan player identity or hash is invalid")
        players[player] = sha
    pairs = {}
    for pair in plan["pairs"]:
        if type(pair) is not dict or type(pair.get("id")) is not str or pair["id"] in pairs:
            raise ValueError("frozen plan pair identity is invalid")
        names, opening = pair.get("players"), pair.get("opening")
        if (type(names) is not list or len(names) != 2 or names[0] == names[1] or
                any(type(name) is not str or name not in players for name in names) or
                type(opening) is not dict or type(opening.get("id")) is not str or
                type(opening.get("moves")) is not list or
                any(type(move) is not str for move in opening["moves"])):
            raise ValueError("frozen plan pair content is invalid")
        pairs[pair["id"]] = pair
    if set(pairs) != set(expected_pairs):
        raise ValueError("frozen plan pair identities differ from collection scope")
    runner = plan.get("runner")
    if (type(runner) is not dict or type(runner.get("sha256")) is not str or
            len(runner["sha256"]) != 64 or
            any(c not in "0123456789abcdef" for c in runner["sha256"]) or
            type(plan.get("bank_id")) is not str or len(plan["bank_id"]) != 64 or
            any(c not in "0123456789abcdef" for c in plan["bank_id"])):
        raise ValueError("frozen plan runner or bank hash is invalid")
    for state in results.games.values():
        pair = pairs.get(state.pair)
        if pair is None:
            continue  # Other stages can coexist in the same journal.
        spec = state.spec
        leg = spec["leg"]
        white, black = pair["players"] if leg == 0 else reversed(pair["players"])
        opening = pair["opening"]
        expected = {"leg": leg, "white": white, "black": black,
                    "opening_id": opening["id"], "opening_moves": opening["moves"],
                    "opening_sha256": digest(opening["moves"]), "bank_id": plan["bank_id"],
                    "profile": profile, "artifact_sha256": {white: players[white], black: players[black]},
                    "runner_sha256": runner["sha256"]}
        if state.game != state.pair + f"-leg{leg}" or any(spec.get(key) != value for key, value in expected.items()):
            raise ValueError("journal game differs from its frozen plan pair")


def collect(rows, campaign, *, expected_pairs=None, profile=None, player_families=None, plan=None):
    rows = list(rows)
    results = CampaignResults.replay(campaign, rows)
    pairs = [pair for pair in results.pairs() if profile is None or pair["profile"] == profile]
    if expected_pairs is not None and len(expected_pairs) != len(set(expected_pairs)):
        raise ValueError("duplicate expected pair identity")
    if plan is not None:
        if expected_pairs is None or profile is None:
            raise ValueError("frozen plan binding requires explicit pair and profile scope")
        bind_plan_games(results, plan, campaign, profile, expected_pairs)
    expected = None if expected_pairs is None else set(expected_pairs)
    if expected is not None:
        unexpected = {pair["pair"] for pair in pairs} - expected
        # A campaign can contain multiple stages; exclude their results, never
        # relabel them as results of this frozen stage.
        pairs = [pair for pair in pairs if pair["pair"] in expected]
    else:
        unexpected = set()
    accepted = {state.game: state for state in results.games.values() if state.accepted}
    gc_status = {game: cooperative_gc_status(rows, campaign, state) for game, state in accepted.items()}
    gc_status = reconcile_cooperative_gc_scopes(rows, campaign, results, accepted, gc_status)
    performance_pairs = [pair for pair in pairs if all(gc_status.get(game) == "clean" for game in pair["games"])]
    performance_ids = {pair["pair"] for pair in performance_pairs}
    performance_excluded = [{"pair": pair["pair"], "games": [
        {"game": game, "attempt": accepted[game].attempt, "cooperative_gc": gc_status[game]}
        for game in pair["games"]]} for pair in pairs if pair["pair"] not in performance_ids]
    table = defaultdict(lambda: {"points": 0.0, "games": 0, "pairs": 0, "W": 0, "D": 0, "L": 0})
    head = defaultdict(float)
    for pair in performance_pairs:
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
                              "complete_pair": state.pair in complete_ids,
                              "cooperative_gc": gc_status[state.game],
                              "performance_included": state.pair in performance_ids})
            if state.pair in performance_ids:
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
    standings = order_standings(standings, player_families)
    complete = bool(expected) and complete_ids == expected
    return {"format": "rove4k-paired-summary-v1", "campaign": campaign, "profile": profile,
            "completed_pairs": pairs, "completed_pair_count": len(pairs),
            "expected_pair_count": None if expected is None else len(expected),
            "missing_pairs": [] if expected is None else sorted(expected - complete_ids),
            "other_stage_pairs_excluded": sorted(unexpected), "campaign_stage_complete": complete,
            "standings": standings, "raw_completed_games": raw_games, "incomplete_attempts": incomplete_games,
            "performance_pairs": performance_pairs, "performance_excluded_pairs": performance_excluded,
            "performance_complete": complete and len(performance_pairs) == len(pairs),
            "selection_ready": plan is not None and complete and len(performance_pairs) == len(pairs),
            "plan_game_binding_checked": plan is not None,
            "scope": "complete colour pairs preserved; performance requires complete owned-controller explicit GC observation; no host attestation, Elo, equivalence or W256 claim"}


def select_high(summary, broad_families, high_players):
    """Choose up to two distinct eligible Rove families from completed broad."""
    if (summary.get("profile") not in ("test-p4", "test-p16") or
            summary.get("selection_ready") is not True or
            summary.get("plan_game_binding_checked") is not True):
        raise ValueError("an incomplete broad stage cannot determine its top two")
    if type(broad_families) is not dict:
        raise ValueError("high selection requires the admitted broad family mapping")
    if summary["profile"] == "test-p16" and ("D" in broad_families.values() or
            any(row.get("family") == "D" for row in high_players)):
        raise ValueError("D is outside the P16/P192 cohort")
    if len({row["family"] for row in high_players}) != len(high_players):
        raise ValueError("high selection requires one qualified artifact per family")
    ordered = order_standings(summary["standings"], broad_families)
    rove = [broad_families[row["player"]] for row in ordered if broad_families[row["player"]] in tuple("ABCDEF")]
    if len(rove) != len(set(rove)):
        raise ValueError("broad selection requires one artifact per Rove family")
    eligible = {row["family"]: row["id"] for row in high_players if row["family"] in tuple("ABCDEF")}
    selected, families = [], set()
    for standing in ordered:
        family = broad_families[standing["player"]]
        if family in eligible and family not in families:
            selected.append(eligible[family])
            families.add(family)
            if len(families) == 2:
                break
    selected += sorted(row["id"] for row in high_players if row["family"] in ("ice4", "c4ke"))
    broad = "P4" if summary["profile"] == "test-p4" else "P16"
    high = "P28" if broad == "P4" else "P192"
    return {"players": selected, "rove_families": sorted(families),
            "partial": len(families) < 2 or sum(row["family"] in ("ice4", "c4ke") for row in high_players) < 2,
            "selection": f"complete {broad} pair points, tied head-to-head, Sonneborn-Berger, fixed family ID; among {high}-qualified families"}


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
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "test-p16", "test-p192"))
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    expected = families = plan = None
    if args.plan:
        # Use the same frozen-plan replay as stage execution and high
        # selection. A self-hashed subset is not a validated schedule.
        try:
            from . import run
        except ImportError:
            import run
        value, _ = run.load_plan(args.plan)
        if (value.get("format") != "rove4k-campaign-plan-v1" or
                digest(value.get("content")) != value.get("sha256") or
                value["content"].get("campaign") != args.campaign or
                args.profile is not None and value["content"].get("profile") != args.profile):
            parser.error("frozen plan identity/campaign/profile differs")
        args.profile = value["content"]["profile"]
        plan = value["content"]
        expected = [row["id"] for row in value["content"]["pairs"]]
        families = {}
        for row in value["content"]["registry"]["players"]:
            artifact = row["artifact"]
            if artifact["id"] in families:
                parser.error("frozen plan contains duplicate player identities")
            families[artifact["id"]] = artifact["family"]
    summary = collect(read_journal(args.journal, args.campaign), args.campaign,
                      expected_pairs=expected, profile=args.profile, player_families=families, plan=plan)
    write_summary(summary, args.out)
    print(json.dumps({"completed_pairs": summary["completed_pair_count"], "stage_complete": summary["campaign_stage_complete"]}))


if __name__ == "__main__":
    main()
