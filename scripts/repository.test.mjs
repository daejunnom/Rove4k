import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { run } from './repository.mjs';

function git(cwd, ...args) {
  const result = spawnSync('git', args, { cwd, encoding: 'utf8', timeout: 30000 });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function fixture(t) {
  const root = fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(), 'rove4k-repository-')));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const remote = path.join(root, 'origin.git');
  const repo = path.join(root, 'repo');
  fs.mkdirSync(repo);
  git(root, 'init', '--bare', '--quiet', remote);
  git(repo, 'init', '--quiet', '--initial-branch=main');
  git(repo, 'config', 'user.name', 'Repository fixture');
  git(repo, 'config', 'user.email', 'repository-fixture@example.invalid');
  fs.writeFileSync(path.join(repo, 'input.txt'), 'preserved source\n');
  fs.writeFileSync(path.join(repo, '.gitignore'), 'ignored/\n');
  git(repo, 'add', 'input.txt', '.gitignore');
  git(repo, 'commit', '--quiet', '-m', 'fixture baseline');
  git(repo, 'branch', 'develop');
  git(repo, 'remote', 'add', 'origin', remote);
  git(repo, 'push', '--quiet', 'origin', 'main', 'develop');
  const base = git(repo, 'rev-parse', 'HEAD');
  return { root, remote, repo, base };
}

function begin(f, branch = 'feature/example') {
  const worktree = path.join(f.root, branch.replaceAll('/', '-'));
  const args = ['start', '--branch', branch, '--worktree', worktree, '--owner', 'fixture-task'];
  return { worktree, args };
}

test('PR routing accepts integration and release paths, and rejects ordinary feature contributions to main', () => {
  assert.equal(run(['pr-check', '--base', 'develop', '--head', 'feature/compression']).allowed, true);
  assert.equal(run(['pr-check', '--base', 'main', '--head', 'release/nvcompact-0.4']).allowed, true);
  assert.equal(run(['pr-check', '--base', 'main', '--head', 'develop']).allowed, true);
  assert.equal(run(['pr-check', '--base', 'develop', '--head', 'main']).allowed, true);
  assert.throws(() => run(['pr-check', '--base', 'main', '--head', 'feature/compression']), { code: 'invalid-pr-route' });
  assert.throws(() => run(['pr-check', '--base', 'develop', '--head', 'develop']), { code: 'invalid-pr-route' });
});

test('start previews without mutation, then creates one locked owned worktree at the reviewed current remote base', t => {
  const f = fixture(t);
  fs.writeFileSync(path.join(f.repo, 'unshared.txt'), 'other task\n');
  const b = begin(f);
  const preview = run(b.args, f.repo);
  assert.equal(preview.executed, false);
  assert.equal(preview.base_sha, f.base);
  assert.equal(fs.existsSync(b.worktree), false);
  assert.throws(() => run([...b.args, '--execute', '--expected-base', '0'.repeat(40)], f.repo), { code: 'base-changed' });
  assert.equal(fs.existsSync(b.worktree), false);
  const result = run([...b.args, '--execute', '--expected-base', f.base], f.repo);
  assert.equal(result.executed, true);
  assert.equal(git(b.worktree, 'rev-parse', 'HEAD'), f.base);
  assert.equal(git(f.repo, 'branch', '--show-current'), 'main');
  assert.equal(fs.readFileSync(path.join(f.repo, 'unshared.txt'), 'utf8'), 'other task\n');
  assert.match(git(f.repo, 'worktree', 'list', '--porcelain'), /locked Rove4k owner fixture-task/);
  const owner = JSON.parse(fs.readFileSync(result.ownership_record, 'utf8'));
  assert.equal(owner.state, 'created');
  assert.equal(owner.branch, 'feature/example');
  assert.equal(git(b.worktree, 'for-each-ref', '--format=%(upstream)', 'refs/heads/feature/example'), '');
  assert.throws(() => run(b.args, f.repo), { code: 'path-exists' });
});

test('start rejects stale remote base and protected or reused branches without modifying source or target', t => {
  const f = fixture(t);
  const b = begin(f);
  const other = path.join(f.root, 'other');
  git(f.root, 'clone', '--quiet', f.remote, other);
  git(other, 'config', 'user.name', 'Other fixture');
  git(other, 'config', 'user.email', 'other@example.invalid');
  git(other, 'switch', '--quiet', 'develop');
  fs.writeFileSync(path.join(other, 'new.txt'), 'advanced remote\n');
  git(other, 'add', 'new.txt');
  git(other, 'commit', '--quiet', '-m', 'remote advanced');
  git(other, 'push', '--quiet', 'origin', 'develop');
  assert.throws(() => run(b.args, f.repo), { code: 'stale-base' });
  assert.equal(fs.existsSync(b.worktree), false);
  assert.throws(() => run(['start', '--branch', 'main'], f.repo), { code: 'protected-branch' });
  assert.equal(git(f.repo, 'rev-parse', 'HEAD'), f.base);
});

test('share plan targets the feature ref explicitly even when an incorrect upstream points to main', t => {
  const f = fixture(t);
  git(f.repo, 'switch', '--quiet', '-c', 'feature/share');
  git(f.repo, 'branch', '--set-upstream-to=origin/main');
  fs.writeFileSync(path.join(f.repo, 'input.txt'), 'WIP change\n');
  git(f.repo, 'add', 'input.txt');
  const before = git(f.repo, 'status', '--porcelain');
  const unobserved = run(['share-plan'], f.repo);
  assert.equal(unobserved.push_argv, null);
  const plan = run(['share-plan', '--remote-check'], f.repo);
  assert.deepEqual(plan.push_argv, ['git', 'push', 'origin', 'HEAD:refs/heads/feature/share']);
  assert.deepEqual(plan.staged_paths, ['input.txt']);
  assert.equal(git(f.repo, 'status', '--porcelain'), before);
  assert.equal(git(f.repo, 'ls-remote', '--heads', 'origin', 'refs/heads/feature/share'), '');
  assert.throws(() => run(['share-plan', '--execute'], f.repo), { code: 'invalid-arguments' });
});

test('cleanup observes ignored and untracked data, owner mismatch and active checkout without deleting anything', t => {
  const f = fixture(t);
  const b = begin(f);
  run([...b.args, '--execute', '--expected-base', f.base], f.repo);
  fs.mkdirSync(path.join(b.worktree, 'ignored'));
  fs.writeFileSync(path.join(b.worktree, 'ignored', 'evidence.dat'), 'retained failure\n');
  fs.writeFileSync(path.join(b.worktree, 'notes.txt'), 'not committed\n');
  git(b.worktree, 'push', '--quiet', 'origin', 'HEAD:refs/heads/feature/example');
  const args = ['cleanup-plan', '--branch', 'feature/example', '--owner', 'fixture-task', '--remote-check'];
  const plan = run(args, f.repo);
  assert.equal(plan.remote_preservation_observed, true);
  assert.equal(plan.eligible_for_automatic_deletion, false);
  assert.ok(plan.blockers.includes('worktree-has-unpreserved-or-unobserved-files'));
  assert.ok(plan.blockers.includes('worktree-still-attached'));
  assert.ok(plan.worktrees[0].changes.some(entry => entry === '!! ignored/'));
  assert.ok(plan.worktrees[0].changes.some(entry => entry === '?? notes.txt'));
  assert.ok(run(args, b.worktree).blockers.includes('current-checkout'));
  const wrong = run(['cleanup-plan', '--branch', 'feature/example', '--owner', 'other'], f.repo);
  assert.ok(wrong.blockers.includes('ownership-not-established'));
  assert.equal(fs.readFileSync(path.join(b.worktree, 'ignored', 'evidence.dat'), 'utf8'), 'retained failure\n');
  assert.equal(git(b.worktree, 'branch', '--show-current'), 'feature/example');
});

test('storage is bounded, does not follow links, and never reclaims retained files', t => {
  const f = fixture(t);
  const storage = path.join(f.root, 'artifacts');
  const outside = path.join(f.root, 'outside');
  fs.mkdirSync(storage);
  fs.mkdirSync(outside);
  fs.writeFileSync(path.join(storage, 'cache.bin'), Buffer.alloc(8));
  fs.writeFileSync(path.join(storage, 'report.txt'), 'keep');
  fs.writeFileSync(path.join(storage, '__proto__'), 'x');
  fs.writeFileSync(path.join(outside, 'not-counted.bin'), Buffer.alloc(128));
  fs.symlinkSync(outside, path.join(storage, 'external-link'), process.platform === 'win32' ? 'junction' : 'dir');
  const result = run(['storage', '--root', storage, '--budget-bytes', '10'], f.repo);
  assert.equal(result.logical_bytes, 13);
  assert.equal(result.groups.__proto__, 1);
  assert.equal(result.within_budget, false);
  assert.equal(result.symlinks_not_followed, 1);
  assert.equal(result.deletion_performed, false);
  const limited = run(['storage', '--root', storage, '--max-entries', '1'], f.repo);
  assert.equal(limited.complete, false);
  assert.equal(limited.within_budget, null);
  assert.equal(fs.statSync(path.join(outside, 'not-counted.bin')).size, 128);
  assert.equal(fs.readFileSync(path.join(storage, 'report.txt'), 'utf8'), 'keep');
  assert.throws(() => run(['storage', '--root', f.repo], f.repo), { code: 'unsafe-path' });
});

test('worktree creation rejects symlink parents and never adopts an existing directory', t => {
  const f = fixture(t);
  const existing = path.join(f.root, 'existing');
  fs.mkdirSync(existing);
  fs.writeFileSync(path.join(existing, 'valuable.txt'), 'preserve');
  const link = path.join(f.root, 'linked');
  fs.symlinkSync(existing, link, process.platform === 'win32' ? 'junction' : 'dir');
  const args = ['start', '--branch', 'feature/path', '--owner', 'fixture-task', '--worktree'];
  assert.throws(() => run([...args, path.join(link, 'child')], f.repo), { code: 'unsafe-path' });
  assert.throws(() => run([...args, existing], f.repo), { code: 'path-exists' });
  const dangling = path.join(f.root, 'dangling');
  fs.symlinkSync(path.join(f.root, 'absent-target'), dangling, process.platform === 'win32' ? 'junction' : 'dir');
  assert.throws(() => run([...args, dangling], f.repo), { code: 'path-exists' });
  assert.throws(() => run([...args, dangling, '--execute', '--expected-base', f.base], f.repo), { code: 'path-exists' });
  assert.equal(fs.lstatSync(dangling).isSymbolicLink(), true);
  assert.equal(fs.existsSync(path.join(f.repo, '.git', 'rove4k-worktrees')), false);
  assert.equal(fs.readFileSync(path.join(existing, 'valuable.txt'), 'utf8'), 'preserve');
  assert.equal(fs.existsSync(path.join(existing, 'child')), false);
});
