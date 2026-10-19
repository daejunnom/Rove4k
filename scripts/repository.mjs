#!/usr/bin/env node
// Repository operations stay outside engine and compression code.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_OUTPUT = 4 * 1024 * 1024;
const PROTECTED = new Set(['main', 'develop']);
const OWNER_FILE_LIMIT = 16 * 1024;

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

function git(cwd, args, allowed = [0]) {
  const result = spawnSync('git', ['--no-optional-locks', ...args], {
    cwd, encoding: 'utf8', timeout: 30000, maxBuffer: MAX_OUTPUT,
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0' },
    windowsHide: true,
  });
  if (result.error || !allowed.includes(result.status)) {
    fail('git-failed', `git ${args[0]}: ${result.error?.message ?? result.stderr.trim() ?? result.status}`);
  }
  return { text: result.stdout, status: result.status };
}

function parseArgs(argv) {
  const [command = 'status', ...rest] = argv;
  const options = {};
  const flags = new Set(['execute', 'remote-check']);
  const values = new Set(['branch', 'worktree', 'owner', 'remote', 'expected-base', 'root', 'budget-bytes', 'max-entries', 'base', 'head']);
  for (let i = 0; i < rest.length; i++) {
    const key = rest[i].replace(/^--/, '');
    if (!rest[i].startsWith('--') || (!flags.has(key) && !values.has(key)) || key in options) {
      fail('invalid-arguments', `Unknown or duplicate option: ${rest[i]}`);
    }
    if (flags.has(key)) options[key] = true;
    else {
      const value = rest[++i];
      if (value === undefined || value.startsWith('--')) fail('invalid-arguments', `Missing --${key} value`);
      options[key] = value;
    }
  }
  const permitted = {
    status: ['remote', 'remote-check'],
    start: ['branch', 'worktree', 'owner', 'remote', 'expected-base', 'execute'],
    'share-plan': ['remote', 'remote-check'],
    'cleanup-plan': ['branch', 'owner', 'remote', 'remote-check'],
    storage: ['root', 'budget-bytes', 'max-entries'],
    'pr-check': ['base', 'head'],
    help: [],
  };
  if (!Object.hasOwn(permitted, command)) fail('invalid-arguments', `Unknown command: ${command}`);
  for (const key of Object.keys(options)) {
    if (!permitted[command].includes(key)) fail('invalid-arguments', `--${key} is not valid for ${command}`);
  }
  return { command, options };
}

function within(parent, child) {
  const relative = path.relative(parent, child);
  return relative === '' || (relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative));
}

function realDirectory(directory) {
  const absolute = path.resolve(directory);
  const root = path.parse(absolute).root;
  let current = root;
  for (const part of absolute.slice(root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink() || !stat.isDirectory()) fail('unsafe-path', `Directory is a link or not a directory: ${current}`);
  }
  const real = fs.realpathSync.native(absolute);
  if (path.relative(real, absolute) !== '') fail('unsafe-path', `Directory does not resolve to itself: ${absolute}`);
  return real;
}

function worktrees(cwd) {
  const records = [];
  let record;
  for (const field of git(cwd, ['worktree', 'list', '--porcelain', '-z']).text.split('\0')) {
    if (field.startsWith('worktree ')) {
      record = { path: field.slice(9) };
      records.push(record);
    } else if (field && record) {
      const split = field.indexOf(' ');
      record[split < 0 ? field : field.slice(0, split)] = split < 0 ? true : field.slice(split + 1);
    }
  }
  return records;
}

function context(cwd) {
  const overrides = Object.keys(process.env).filter(key => /^(GIT_DIR|GIT_WORK_TREE|GIT_INDEX_FILE|GIT_COMMON_DIR|GIT_OBJECT_DIRECTORY|GIT_ALTERNATE_OBJECT_DIRECTORIES|GIT_CONFIG|GIT_CONFIG_PARAMETERS|GIT_CONFIG_COUNT|GIT_CONFIG_KEY_\d+|GIT_CONFIG_VALUE_\d+)$/.test(key));
  if (overrides.length) fail('ambient-git-override', `Run from the selected checkout without Git path/config overrides: ${overrides.join(', ')}`);
  const root = fs.realpathSync.native(git(cwd, ['rev-parse', '--show-toplevel']).text.trim());
  return {
    root,
    common: realDirectory(git(root, ['rev-parse', '--path-format=absolute', '--git-common-dir']).text.trim()),
    head: git(root, ['rev-parse', 'HEAD']).text.trim(),
    branch: git(root, ['symbolic-ref', '--quiet', '--short', 'HEAD'], [0, 1]).text.trim() || null,
    worktrees: worktrees(root),
  };
}

function branchName(ctx, branch) {
  if (typeof branch !== 'string' || git(ctx.root, ['check-ref-format', '--branch', branch], [0, 128]).status !== 0) {
    fail('invalid-branch', 'A valid explicit branch name is required');
  }
  if (PROTECTED.has(branch) || !/^(feature|release|hotfix)\/[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(branch)) {
    fail('protected-branch', 'Work must use feature/*, release/* or hotfix/*, never main/develop');
  }
  return branch;
}

function remoteName(ctx, options) {
  const remote = options.remote ?? 'origin';
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(remote) || !git(ctx.root, ['remote']).text.split('\n').includes(remote)) {
    fail('invalid-remote', 'Select an existing named remote');
  }
  return remote;
}

function remoteHead(ctx, remote, branch) {
  const ref = `refs/heads/${branch}`;
  const rows = git(ctx.root, ['ls-remote', '--heads', remote, ref]).text.trim().split('\n').filter(Boolean);
  if (rows.length === 0) return null;
  const fields = rows[0].split('\t');
  if (rows.length !== 1 || fields[1] !== ref || !/^[a-f0-9]{40,64}$/.test(fields[0])) {
    fail('remote-response', 'Remote did not return one exact branch reference');
  }
  return fields[0];
}

function localRef(ctx, ref) {
  return git(ctx.root, ['rev-parse', '--verify', '--quiet', `${ref}^{commit}`], [0, 1]).text.trim() || null;
}

function workingChanges(directory) {
  // Matching ignored directories are reported without traversing their contents.
  return git(directory, ['status', '--porcelain=v1', '-z', '--untracked-files=normal', '--ignored=matching']).text
    .split('\0').filter(Boolean);
}

function ownerPath(ctx, branch) {
  const digest = createHash('sha256').update(branch).digest('hex');
  return path.join(ctx.common, 'rove4k-worktrees', `${digest}.json`);
}

function readOwner(ctx, branch) {
  const filename = ownerPath(ctx, branch);
  if (!fs.existsSync(path.dirname(filename))) return null;
  realDirectory(path.dirname(filename));
  let fd;
  try {
    fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW ?? 0));
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > OWNER_FILE_LIMIT || fs.lstatSync(filename).isSymbolicLink()) {
      fail('unsafe-owner', 'Worktree ownership record must be a small regular file');
    }
    const value = JSON.parse(fs.readFileSync(fd, 'utf8'));
    if (value.version !== 1 || value.common !== ctx.common || value.branch !== branch || typeof value.owner !== 'string') {
      fail('owner-mismatch', 'Ownership record is not bound to this repository and branch');
    }
    return value;
  } finally {
    fs.closeSync(fd);
  }
}

function status(ctx, options) {
  const remote = remoteName(ctx, options);
  return {
    command: 'status', ...ctx,
    changes: workingChanges(ctx.root),
    upstream: git(ctx.root, ['for-each-ref', '--format=%(upstream:short)', `refs/heads/${ctx.branch ?? ''}`]).text.trim() || null,
    remote,
    remote_checked: Boolean(options['remote-check']),
    remote_tip: options['remote-check'] && ctx.branch ? remoteHead(ctx, remote, ctx.branch) : null,
    activity: 'not-observed; git state is not process lifetime evidence',
  };
}

function start(ctx, options) {
  const branch = branchName(ctx, options.branch);
  const owner = options.owner;
  if (!owner || !/^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}$/.test(owner)) fail('invalid-owner', 'Specify a stable task owner with --owner');
  if (!options.worktree || !path.isAbsolute(options.worktree)) fail('unsafe-path', '--worktree must be an absolute new path');
  const target = path.join(realDirectory(path.dirname(options.worktree)), path.basename(options.worktree));
  if (fs.existsSync(target)) fail('path-exists', 'The worktree target already exists; it will not be adopted or emptied');
  if (ctx.worktrees.some(w => within(path.resolve(w.path), target) || within(target, path.resolve(w.path)))) {
    fail('unsafe-path', 'The new worktree must be outside all existing worktrees');
  }
  if (localRef(ctx, `refs/heads/${branch}`) || readOwner(ctx, branch)) fail('branch-exists', 'Reuse the existing branch and its recorded owner');
  const remote = remoteName(ctx, options);
  if (remoteHead(ctx, remote, branch)) fail('branch-exists', 'A remote branch already exists; inspect and reuse it');
  const baseBranch = branch.startsWith('hotfix/') ? 'main' : 'develop';
  const base = remoteHead(ctx, remote, baseBranch);
  const tracking = localRef(ctx, `refs/remotes/${remote}/${baseBranch}`);
  if (!base || base !== tracking) fail('stale-base', `Fetch ${remote}/${baseBranch}; its local object and current remote tip must agree`);
  const plan = { command: 'start', branch, worktree: target, owner, remote, base_branch: baseBranch, base_sha: base, executed: false };
  if (!options.execute) return plan;
  if (options['expected-base'] !== base) fail('base-changed', 'Use --expected-base with the exact SHA from the reviewed start plan');

  const filename = ownerPath(ctx, branch);
  if (!fs.existsSync(path.dirname(filename))) fs.mkdirSync(path.dirname(filename), { mode: 0o700 });
  realDirectory(path.dirname(filename));
  const value = { version: 1, state: 'reserved', common: ctx.common, branch, worktree: target, owner, base, created: new Date().toISOString() };
  const fd = fs.openSync(filename, 'wx', 0o600);
  try {
    fs.writeFileSync(fd, `${JSON.stringify(value, null, 2)}\n`);
    fs.fsyncSync(fd);
    // An interrupted reservation is deliberately retained, never auto-stolen.
    fs.mkdirSync(target, { mode: 0o700 });
    git(ctx.root, ['worktree', 'add', '--lock', '--reason', `Rove4k owner ${owner}`, '--no-track', '-b', branch, target, base]);
    value.state = 'created';
    fs.ftruncateSync(fd, 0);
    fs.writeSync(fd, `${JSON.stringify(value, null, 2)}\n`, 0, 'utf8');
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  return { ...plan, executed: true, lock: 'owned worktree; release requires a separate lifetime review', ownership_record: filename };
}

function sharePlan(ctx, options) {
  const branch = branchName(ctx, ctx.branch);
  const remote = remoteName(ctx, options);
  const checked = Boolean(options['remote-check']);
  const tip = checked ? remoteHead(ctx, remote, branch) : null;
  const tipKnown = tip === null || localRef(ctx, tip) !== null;
  const fastForward = checked && tipKnown && (tip === null || git(ctx.root, ['merge-base', '--is-ancestor', tip, ctx.head], [0, 1]).status === 0);
  return {
    command: 'share-plan', branch, head: ctx.head, remote, remote_checked: checked, remote_tip: tip,
    fast_forward_observed: fastForward,
    staged_paths: git(ctx.root, ['diff', '--cached', '--name-only', '-z']).text.split('\0').filter(Boolean),
    changes: workingChanges(ctx.root),
    review: 'Review and commit intended content, then refresh this plan. Push publishes committed HEAD, not staged files. Known failures belong in the same draft PR; this command does not stage, commit or push.',
    push_argv: fastForward ? ['git', 'push', remote, `HEAD:refs/heads/${branch}`] : null,
    blockers: checked ? (fastForward ? [] : ['remote-tip-needs-fetch-or-integration']) : ['fresh-remote-tip-not-observed'],
  };
}

function cleanupPlan(ctx, options) {
  const branch = branchName(ctx, options.branch);
  const owner = readOwner(ctx, branch);
  const tip = localRef(ctx, `refs/heads/${branch}`);
  const attached = ctx.worktrees.filter(w => w.branch === `refs/heads/${branch}`);
  const blockers = [];
  if (!tip) blockers.push('local-branch-missing');
  if (!owner || owner.owner !== options.owner) blockers.push('ownership-not-established');
  if (owner && owner.state !== 'created') blockers.push('incomplete-ownership-reservation');
  const trees = attached.map(w => ({ ...w, changes: fs.existsSync(w.path) ? workingChanges(w.path) : null }));
  if (trees.some(w => w.changes === null || w.changes.length)) blockers.push('worktree-has-unpreserved-or-unobserved-files');
  if (trees.length) blockers.push('worktree-still-attached');
  if (branch === ctx.branch) blockers.push('current-checkout');
  const remote = remoteName(ctx, options);
  const checked = Boolean(options['remote-check']);
  const remoteTip = checked ? remoteHead(ctx, remote, branch) : null;
  const baseBranch = branch.startsWith('hotfix/') ? 'main' : 'develop';
  const mergedTip = checked ? remoteHead(ctx, remote, baseBranch) : null;
  const mergedObjectPresent = mergedTip !== null && localRef(ctx, mergedTip) !== null;
  const merged = Boolean(tip && mergedObjectPresent && git(ctx.root, ['merge-base', '--is-ancestor', tip, mergedTip], [0, 1]).status === 0);
  const preserved = Boolean(tip && checked && (tip === remoteTip || merged));
  if (!preserved) blockers.push('exact-tip-not-confirmed-on-remote-or-merged');
  blockers.push('physical-inactivity-and-other-open-PR-use-require-owner-review');
  return {
    command: 'cleanup-plan', branch, tip, owner, worktrees: trees,
    remote_checked: checked, remote_tip: remoteTip, integration_tip: mergedTip, remote_preservation_observed: preserved,
    physical_activity: 'unknown; no PID scan or stale lock inference',
    deletion_performed: false, eligible_for_automatic_deletion: false, blockers,
    review: 'Preserve ignored/untracked data, active work and failure/release evidence. After a separate confirmed owner review, use git worktree remove and git branch -d without force. No cleanup is executed here.',
  };
}

function storage(ctx, options) {
  if (!options.root || !path.isAbsolute(options.root)) fail('unsafe-path', '--root must be an explicit absolute directory');
  const root = realDirectory(options.root);
  if (ctx.worktrees.some(w => within(path.resolve(w.path), root) || within(root, path.resolve(w.path)))) {
    fail('unsafe-path', 'Storage observation must not include a source worktree');
  }
  const positiveInteger = (value, fallback) => {
    const n = value === undefined ? fallback : Number(value);
    if (!Number.isSafeInteger(n) || n <= 0) fail('invalid-budget', 'Budgets must be positive safe integers');
    return n;
  };
  const budget = positiveInteger(options['budget-bytes'], Number.MAX_SAFE_INTEGER);
  const limit = positiveInteger(options['max-entries'], 100000);
  const pending = [root];
  const groups = Object.create(null);
  let entries = 0;
  let bytes = 0;
  let links = 0;
  let complete = true;
  const problems = [];
  while (pending.length && complete) {
    const directory = pending.pop();
    // Recheck each selected directory, including ancestors, before enumeration.
    realDirectory(directory);
    const handle = fs.opendirSync(directory);
    try {
      let entry;
      while ((entry = handle.readSync()) !== null) {
        if (++entries > limit) { complete = false; break; }
        const filename = path.join(directory, entry.name);
        let stat;
        try { stat = fs.lstatSync(filename); }
        catch (error) { problems.push({ path: path.relative(root, filename), code: error.code }); continue; }
        if (stat.isSymbolicLink()) { links++; continue; }
        if (stat.isDirectory()) pending.push(filename);
        else if (stat.isFile()) {
          const group = path.relative(root, filename).split(path.sep)[0];
          if (!Number.isSafeInteger(bytes + stat.size)) fail('size-overflow', 'Observed logical size exceeds safe integer range');
          bytes += stat.size;
          groups[group] = (groups[group] ?? 0) + stat.size;
        } else problems.push({ path: path.relative(root, filename), code: 'non-regular-entry' });
      }
    } finally { handle.closeSync(); }
  }
  return {
    command: 'storage', root, entries_observed: Math.min(entries, limit), logical_bytes: bytes,
    complete: complete && problems.length === 0, budget_bytes: options['budget-bytes'] ? budget : null,
    within_budget: !complete || problems.length ? null : (options['budget-bytes'] ? bytes <= budget : null),
    symlinks_not_followed: links, problems, groups,
    deletion_performed: false,
    limitation: 'Read-only logical length snapshot, not disk allocation, process inactivity, retention approval or a storage quota.',
  };
}

export function run(argv, cwd = process.cwd()) {
  const { command, options } = parseArgs(argv);
  if (command === 'pr-check') {
    const { base, head } = options;
    const source = /^(feature|release|hotfix)\/[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(head ?? '');
    const permitted = (base === 'develop' && (source || head === 'main'))
      || (base === 'main' && (head === 'develop' || /^(release|hotfix)\/[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(head ?? '')));
    if (!permitted || base === head) fail('invalid-pr-route', 'Use feature/* → develop; promote develop/release/*/hotfix/* → main through a PR');
    return { command, base, head, allowed: true, limitation: 'Route only; review, checks, authorization and release eligibility remain separate.' };
  }
  if (command === 'help') return {
    commands: {
      status: '[--remote origin] [--remote-check]',
      start: '--branch feature/topic --worktree /external/topic --owner task-id [--remote origin] [--execute --expected-base SHA]',
      'share-plan': '[--remote origin] [--remote-check]',
      'cleanup-plan': '--branch feature/topic --owner task-id [--remote origin] [--remote-check]',
      storage: '--root /external/artifacts [--budget-bytes N] [--max-entries N]',
      'pr-check': '--base develop --head feature/topic',
    },
    mutations: 'Only start --execute creates a branch, locked worktree and ownership record. All other commands are read-only.',
  };
  const ctx = context(cwd);
  return ({ status, start, 'share-plan': sharePlan, 'cleanup-plan': cleanupPlan, storage })[command](ctx, options);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.stdout.write(`${JSON.stringify(run(process.argv.slice(2)), null, 2)}\n`); }
  catch (error) {
    process.stderr.write(`${JSON.stringify({ error: error.code ?? 'repository-error', message: error.message })}\n`);
    process.exitCode = 1;
  }
}
