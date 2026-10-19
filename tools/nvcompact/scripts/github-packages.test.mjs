import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { checkArchivePaths, checkInventory, checkRequest, checkSourceBytes, mirrorMetadata, registryMetadata, scopedName, workflow } from './github-packages.mjs';
import { hash, json } from './common.mjs';

const config = await json(new URL('./release-config.json', import.meta.url));
const metadata = await json(new URL('../npm/package.json', import.meta.url));
const commit = '1234567890abcdef1234567890abcdef12345678';
const env = { GITHUB_ACTIONS: 'true', GITHUB_EVENT_NAME: 'workflow_dispatch',
  GITHUB_REPOSITORY: config.repository, GITHUB_REF: 'refs/heads/main', GITHUB_SHA: commit,
  GITHUB_WORKFLOW_REF: config.repository + '/.github/workflows/' + workflow + '@refs/heads/main',
  NVC_RELEASE_VERSION: metadata.version, NVC_RELEASE_COMMIT: commit, NVC_RELEASE_OPERATION: 'publish' };

test('registry verification accepts npm 12 single-version arrays without relaxing package identity', () => {
  const expected = { name: scopedName(config), version: metadata.version, repository: config.repository };
  const record = { name: expected.name, version: expected.version, repository: metadata.repository };
  assert.deepEqual(registryMetadata(JSON.stringify(record), expected), record);
  assert.deepEqual(registryMetadata(JSON.stringify([record]), expected), record);
  for (const value of [[], [record, record], null, {}, { ...record, name: 'other' },
    [{ ...record, version: '999.0.0' }], [{ ...record, repository: { url: 'git+https://github.com/other/repo.git' } }]]) {
    assert.throws(() => registryMetadata(JSON.stringify(value), expected));
  }
});

test('the GitHub mirror changes only package name and destination registry', () => {
  const original = structuredClone(metadata);
  const mirror = mirrorMetadata(metadata, config, metadata.version);
  assert.equal(mirror.name, '@daejunnom/nvcompact');
  assert.equal(scopedName(config), mirror.name);
  assert.equal(mirror.publishConfig.registry, 'https://npm.pkg.github.com/');
  assert.deepEqual({ ...mirror, name: metadata.name, publishConfig: metadata.publishConfig }, metadata);
  assert.deepEqual(metadata, original);
  for (const changed of [{ name: 'other' }, { version: '999.0.0' }, { repository: { url: 'git+https://github.com/other/repo.git' } },
    { publishConfig: { registry: 'https://other.invalid/' } }, { private: true }]) {
    assert.throws(() => mirrorMetadata({ ...metadata, ...changed }, config, metadata.version));
  }
});

test('the public source archive must match both reviewed SHA-256 and registry SHA-512', () => {
  const bytes = Buffer.from('owned source archive fixture');
  const integrity = 'sha512-' + createHash('sha512').update(bytes).digest('base64');
  assert.doesNotThrow(() => checkSourceBytes(bytes, hash(bytes), integrity));
  assert.throws(() => checkSourceBytes(Buffer.from('changed'), hash(bytes), integrity));
  assert.throws(() => checkSourceBytes(bytes, hash(bytes), 'sha512-wrong'));
  assert.throws(() => checkSourceBytes(bytes, '', integrity));
});

test('tar extraction rejects additional, duplicate and escaping package entries', () => {
  const files = ['LICENSE', 'README.md', 'package.json', 'bin/nvcompact.mjs', 'lib/cli.mjs',
    'lib/ensure-native.mjs', 'lib/paths.mjs', 'native/runtime.json', 'native/linux-x64/nvcompact'].map(p => 'package/' + p);
  assert.doesNotThrow(() => checkArchivePaths(files));
  for (const changed of [files.slice(1), [...files, 'package/unreviewed'], [...files, files[0]],
    files.map((p, i) => i === 0 ? '../escape' : p)]) assert.throws(() => checkArchivePaths(changed));
});

test('manifest scoping cannot alter native executable or any other packaged file', () => {
  const manifest = mirrorMetadata(metadata, config, metadata.version);
  const original = { 'package.json': { bytes: 1, sha256: 'original' },
    'native/linux-x64/nvcompact': { bytes: 4, sha256: 'native', mode: 0o755 }, LICENSE: { bytes: 3, sha256: 'license' } };
  const mirrored = { ...original, 'package.json': { bytes: 2,
    sha256: hash(Buffer.from(JSON.stringify(manifest, null, 2) + '\n')) } };
  assert.doesNotThrow(() => checkInventory(original, mirrored, manifest));
  assert.throws(() => checkInventory(original, { ...mirrored, LICENSE: { bytes: 3, sha256: 'changed' } }, manifest));
  assert.throws(() => checkInventory(original, { ...mirrored, 'native/linux-x64/nvcompact': {
    ...original['native/linux-x64/nvcompact'], mode: 0o644 } }, manifest));
  assert.throws(() => checkInventory(original, { ...mirrored, extra: {} }, manifest));
  assert.throws(() => checkInventory(original, { ...mirrored, 'package.json': original['package.json'] }, manifest));
});

test('GitHub Packages publication is bound to the exact main workflow and explicit request', () => {
  assert.equal(checkRequest(env, config, metadata.version), 'publish');
  assert.equal(checkRequest({ ...env, NVC_RELEASE_OPERATION: 'prepare' }, config, metadata.version), 'prepare');
  for (const changed of [{ GITHUB_EVENT_NAME: 'pull_request' }, { GITHUB_REF: 'refs/heads/develop' },
    { GITHUB_REPOSITORY: 'other/fork' }, { NVC_RELEASE_COMMIT: '0'.repeat(40) },
    { GITHUB_WORKFLOW_REF: config.repository + '/.github/workflows/nvcompact-publish.yml@refs/heads/main' },
    { NVC_RELEASE_VERSION: '999.0.0' }]) assert.throws(() => checkRequest({ ...env, ...changed }, config, metadata.version));
});
