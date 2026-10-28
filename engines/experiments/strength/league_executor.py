"""Prepare actual P16/P192 Fastchess jobs, without granting scored GO.

The frozen plan, target cgroup and leaf receipts must come from their
respective owners. Their local consistency is not remote host ownership,
global budget authority, reserved memory, or proof of TT page placement.
Scored execution remains unavailable until those owners are connected.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

try:
    from . import diagnostic_candidates, fastchess, league_score_plan, ledger, placement, run, topology, wave
except ImportError:
    import diagnostic_candidates
    import fastchess
    import league_score_plan
    import ledger
    import placement
    import run
    import topology
    import wave


def _write_new(path, value):
    data = ledger.canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def prepare_wave(plan_path, selections, groups, target, out, *, launch_id, plan_sha256=None):
    """Construct placement/Fastchess WaveJobs from a plan without starting it.

    The legacy path uses an admitted frozen plan. Supplying ``plan_sha256``
    instead replays a distinct non-authorizing score draft and derives slots
    from a fresh target topology snapshot; that snapshot is not attestation.

    ``selections`` contains pair, leg, attempt and slot for each game. The
    two engines inherit the same slot via placement before Fastchess exec.
    Inputs must be bound by the caller to owned cgroups; this method checks
    their current identities but does not authenticate their provenance.
    No process is launched and no authorization is requested here.
    """
    if not isinstance(launch_id, str) or not launch_id or len(launch_id) > 32:
        raise ValueError('bounded explicit launch identity required')
    run.ID(launch_id)
    draft = plan_sha256 is not None
    if draft:
        plan_path = diagnostic_candidates._safe_input_path(plan_path)
        if not plan_path.is_file() or plan_path.stat().st_size > 16 << 20:
            raise ValueError('bounded ordinary draft plan required')
        with plan_path.open('rb') as stream:
            plan_bytes = stream.read((16 << 20) + 1)
        envelope = league_score_plan.verify_bytes(plan_bytes, plan_sha256)
        player_rows = None
    else:
        plan_path = run.protected_input(plan_path)
        envelope, player_rows = run.load_plan(plan_path)
    body = envelope['content']
    profile = body['profile']
    if profile not in ('test-p16', 'test-p192'):
        raise ValueError('P16 or P192 frozen plan required')
    if not isinstance(target, dict) or set(target) != {'path', 'device', 'inode'}:
        raise ValueError('original dedicated cgroup identity required')
    target_path = Path(target['path'])
    if (not target_path.is_absolute() or type(target['device']) is not int or target['device'] < 0
            or type(target['inode']) is not int or target['inode'] <= 0):
        raise ValueError('invalid original dedicated cgroup identity')
    live = topology.Topology.snapshot_target(target_path, device=target['device'], inode=target['inode'])
    saved = live if draft else topology.Topology.from_record(body['topology'])
    if not draft and live.to_record() != saved.to_record():
        raise ValueError('target topology or effective masks changed since plan freezing')
    planned, controller_cpus = run.league_placement(saved, profile)
    if not draft and ([json.loads(json.dumps(s.to_record())) for s in planned] != body['slots']
            or controller_cpus != body['controller_cpus']):
        raise ValueError('frozen slots or controller CPUs differ from the plan')
    slot_map = {slot.id: slot for slot in planned}
    maximum = 11 if profile == 'test-p16' else 1
    if len(slot_map) != maximum or not isinstance(selections, (list, tuple)) or not 1 <= len(selections) <= maximum:
        raise ValueError('wave exceeds the profile slot count')
    if not isinstance(groups, dict) or set(groups) != set(slot_map):
        raise ValueError('one original owned cgroup receipt per planned slot required')
    seen_groups = set()
    for slot_id, group in groups.items():
        if not isinstance(group, dict):
            raise ValueError('invalid cgroup receipt')
        path = Path(group.get('path', ''))
        try:
            relative = path.relative_to(target_path)
        except ValueError as error:
            raise ValueError('slot cgroup escapes original target') from error
        slot = slot_map[slot_id]
        if (not relative.parts or '..' in relative.parts or group.get('cpus') != list(slot.cpus)
                or group.get('memory_nodes') != list(slot.memory_nodes)):
            raise ValueError('cgroup CPU or NUMA masks differ from frozen slot')
        identity = (group.get('device'), group.get('inode'))
        if identity in seen_groups:
            raise ValueError('two slots cannot share the same cgroup identity')
        seen_groups.add(identity)
        placement.verify_cgroup_live(group)
    if draft:
        pairs = {item['id']: {**item, 'opening': {'id': item['opening_id'], 'moves': item['opening_moves']}}
                 for item in body['pairs']}
        players = {row['identity']['id']: SimpleNamespace(
            id=row['identity']['id'], path=Path(row['whole_path']), tt_bytes=row['identity']['tt_bytes'],
            sha256=row['identity']['sha256'], uci=row['uci']) for row in body['players']}
    else:
        pairs = {item['id']: item for item in body['pairs']}
        players = {row['artifact'].id: row['artifact'] for row in player_rows}
    rows, seen_games, seen_slots = [], set(), set()
    for selection in selections:
        if not isinstance(selection, dict) or set(selection) != {'pair', 'leg', 'attempt', 'slot'}:
            raise ValueError('exact pair, leg, attempt and slot selection required')
        pair = pairs.get(selection['pair'])
        leg, attempt, slot_id = selection['leg'], selection['attempt'], selection['slot']
        if (pair is None or type(leg) is not int or leg not in (0, 1) or type(attempt) is not int
                or not 0 <= attempt <= 999 or slot_id not in slot_map or slot_id in seen_slots):
            raise ValueError('invalid game attempt or duplicate wave slot')
        game = pair['id'] + f'-leg{leg}'
        if game in seen_games:
            raise ValueError('one game cannot occupy multiple wave slots')
        seen_games.add(game)
        seen_slots.add(slot_id)
        white, black = pair['players'] if leg == 0 else tuple(reversed(pair['players']))
        if white not in players or black not in players:
            raise ValueError('game players do not match admitted plan')
        memory = groups[slot_id].get('memory_max')
        tt = [getattr(players[name], 'tt_bytes', None) for name in (white, black)]
        if (type(memory) is not int or any(type(n) is not int or n <= 0 for n in tt)
                or memory < sum(tt)):
            raise ValueError('slot memory cannot contain both frozen TT extents')
        rows.append((pair, leg, attempt, slot_id, game, white, black))
    out = diagnostic_candidates._safe_output_path(out) if draft else run.external_new(out)
    out.mkdir(mode=0o700, parents=True)
    jobs, specs = [], {}
    runner = Path(body['inputs']['runner_binary']) if draft else run.bundle_path(plan_path.parent, body['runner']['path'])
    openings = Path(body['opening_pgn']['path']) if draft else run.bundle_path(plan_path.parent, body['opening_pgn'])
    for pair, leg, attempt, slot_id, game, white, black in rows:
        slot = slot_map[slot_id]
        job_id = game + f'.a{attempt:03d}.x{launch_id}'
        job_out = out / 'jobs' / game / f'attempt-{attempt:03d}-launch-{launch_id}'
        slot_file = out / f'placement-{slot_id}.json'
        record = out / f'placement-observed-{job_id}.json'
        _write_new(slot_file, {'slot': slot.to_record(), 'cgroup': groups[slot_id],
                               'saved_ancestor_cpus': list(saved.allowed_cpus),
                               'saved_ancestor_nodes': list(saved.allowed_nodes)})
        def command(name):
            uci = getattr(players[name], 'uci', None)
            options = {} if uci is None else {'hash_mib': uci['hash_mib'], 'threads': uci['threads']}
            return fastchess.EngineCommand(name, (str(players[name].path),), **options)
        runner_argv = fastchess.single_game_argv(
            runner, command(white), command(black),
            opening_pgn=openings, opening_start=pair['opening_index'], out=job_out)
        argv = (sys.executable, str(run.HERE / 'placement.py'), '--slot', str(slot_file),
                '--record', str(record), '--', *runner_argv)
        identity = {'leg': leg, 'white': white, 'black': black, 'opening_id': pair['opening']['id'],
                    'opening_moves': pair['opening']['moves'], 'opening_sha256': ledger.digest(pair['opening']['moves']),
                    'bank_id': body['bank_id'], 'profile': profile,
                    'artifact_sha256': {name: players[name].sha256 for name in (white, black)},
                    'runner_sha256': body['runner']['sha256'], 'slot': slot_id}
        if draft:
            identity['uci'] = {name: players[name].uci for name in (white, black)}
        start_job = {'campaign': body['campaign'], 'pair': pair['id'], 'game': game,
                     'attempt': attempt, 'slot': slot_id, 'artifacts': [white, black],
                     'opening': pair['opening']['id'], 'launch_id': launch_id,
                     'attempt_id': run.attempt_identity(body['campaign'], pair['id'], game, attempt, job_id),
                     'identity_sha256': ledger.digest(identity)}
        jobs.append(wave.WaveJob(job_id, argv, {'TZ': 'UTC', 'LANG': 'C.UTF-8'}, start_job, job_out))
        specs[job_id] = {'pair': pair['id'], 'game': game, 'attempt': attempt, 'identity': identity,
                         'slot': slot.to_record(), 'cgroup': groups[slot_id],
                         'placement_record': str(record)}
    _write_new(out / 'prepared-wave.json', {'format': ('rove4k-league-draft-prepared-wave-v1' if draft
                                                       else 'rove4k-league-prepared-wave-v1'),
               'plan_sha256': envelope['sha256'], 'profile': profile, 'launch_id': launch_id,
               'jobs': [{'identity': job.identity, 'argv': list(job.argv), 'start_job': job.start_job,
                         'out': str(job.out), 'spec': specs[job.identity]} for job in jobs],
               'scope': 'prepared jobs only; no process, authority or memory reservation',
               **({'draft_only': True, 'score_authorized': False, 'go_authorized': False,
                   'live_topology_snapshot_not_attestation': True} if draft else {})})
    return jobs, specs


def prepare_draft_wave(plan_path, plan_sha256, selections, groups, target, out, *, launch_id):
    """Replay a draft and prepare its real commands without starting a game."""
    return prepare_wave(plan_path, selections, groups, target, out,
                        launch_id=launch_id, plan_sha256=plan_sha256)


def run_readiness(plan_path, selections, groups, target, out, *, launch_id, admission_seconds):
    """Keep process creation closed until its ownership contract exists.

    A scored plan already requires qualifications and therefore cannot serve
    as the diagnostic needed to earn them. Prequalified single-engine
    diagnostics have their own owner. A two-engine READY path must first bind
    non-scoring candidates, immutable runner inputs and crash recovery; merely
    returning process observations would not settle ownership after failure.
    """
    raise RuntimeError('prequalification READY requires diagnostic candidates and durable process ownership')


def run_scored(*args, **kwargs):
    """Do not start processes until authenticated global admission exists."""
    raise RuntimeError('P16/P192 score GO requires authenticated global budget and host fencing')
