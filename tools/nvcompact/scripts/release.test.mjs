import assert from 'node:assert/strict';
import test from 'node:test';
import { checkBundle, checkCiRequest, checkPackage, checkRegistryState, checkRuntime, publicationArgs } from './release.mjs';
import { hash, json, packageRoot } from './common.mjs';
import path from 'node:path';

const config = await json(new URL('./release-config.json', import.meta.url));
const metadata = await json(path.join(packageRoot, 'package.json'));
const commit = '1234567890abcdef1234567890abcdef12345678';
const env = { GITHUB_ACTIONS: 'true', GITHUB_EVENT_NAME: 'workflow_dispatch',
  GITHUB_REPOSITORY: config.repository, GITHUB_REF: `refs/heads/${config.release_branch}`,
  GITHUB_WORKFLOW_REF: `${config.repository}/.github/workflows/${config.workflow}@refs/heads/${config.release_branch}`,
  GITHUB_SHA: commit, NVC_RELEASE_COMMIT: commit, NVC_RELEASE_VERSION: metadata.version,
  NVC_RELEASE_OPERATION: 'prepare' };

test('a release request cannot switch its source, workflow or operation implicitly', () => {
  assert.equal(checkCiRequest(env, config, metadata.version), 'prepare');
  for (const operation of ['stage', 'publish']) {
    assert.equal(checkCiRequest({ ...env, NVC_RELEASE_OPERATION: operation }, config, metadata.version), operation);
    const args = publicationArgs(operation, '/owned path/nvcompact.tgz', config, true);
    assert(args.includes('--dry-run=false'), 'an inherited npm dry-run must not become a false published result');
    assert(args.includes('--force=false'));
    assert(args.includes('--provenance'));
  }
  for (const changed of [{ GITHUB_EVENT_NAME: 'pull_request' }, { GITHUB_REF: 'refs/heads/develop' },
    { GITHUB_REPOSITORY: 'someone/fork' }, { NVC_RELEASE_COMMIT: '0'.repeat(40) },
    { NVC_RELEASE_VERSION: '999.0.0' }, { NVC_RELEASE_OPERATION: '' },
    { GITHUB_WORKFLOW_REF: `${config.repository}/.github/workflows/another.yml@refs/heads/main` }]) {
    assert.throws(() => checkCiRequest({ ...env, ...changed }, config, metadata.version));
  }
});

test('name reuse, version overwrite and missing first publish are distinct failures', () => {
  const existing = { name: config.package, maintainers: [{ name: config.npm_owner }], versions: {} };
  assert.doesNotThrow(() => checkRegistryState(null, config, metadata.version, false));
  assert.throws(() => checkRegistryState(null, config, metadata.version, true), /first manual publish/);
  assert.doesNotThrow(() => checkRegistryState(existing, config, metadata.version, true));
  assert.throws(() => checkRegistryState({ ...existing, maintainers: [{ name: 'another-owner' }] }, config, metadata.version, false), /owner/);
  assert.throws(() => checkRegistryState({ ...existing, versions: { [metadata.version]: {} } }, config, metadata.version, true), /already exists/);
});

test('a changed or unverified tarball cannot reuse a prepared release identity', () => {
  const bytes = Buffer.from('owned example of a release boundary');
  const record = { format: 'nvcompact.release.v1', package: metadata.name, version: metadata.version,
    registry: config.registry, npm_owner: config.npm_owner, repository: config.repository,
    dist_tag: config.dist_tag, platform_key: config.platform_key, rust_target: config.rust_target,
    tarball: `${metadata.name}-${metadata.version}.tgz`, bytes: bytes.length, sha256: hash(bytes),
    validation: { status: 'pass', package_sha256: hash(bytes) } };
  assert.doesNotThrow(() => checkBundle(record, bytes, config, metadata));
  assert.throws(() => checkBundle(record, Buffer.from('changed artifact'), config, metadata));
  assert.throws(() => checkBundle({ ...record, validation: { status: 'not_run' } }, bytes, config, metadata));
  assert.throws(() => checkBundle({ ...record, tarball: '../another.tgz' }, bytes, config, metadata));
  const native = Buffer.from('owned executable bytes');
  const nativeRecord = { ...record, source_sha256: 'source identity', runtime_sha256: hash(native),
    validation: { ...record.validation, runtime_sha256: hash(native) } };
  const runtime = { format: 'nvcompact.npm-native.v1', version: metadata.version,
    platform_key: config.platform_key, rust_host: config.rust_target, source_sha256: 'source identity',
    bytes: native.length, sha256: hash(native) };
  assert.doesNotThrow(() => checkRuntime(nativeRecord, runtime, native));
  assert.throws(() => checkRuntime({ ...nativeRecord, source_sha256: 'another source' }, runtime, native));
  assert.throws(() => checkRuntime({ ...nativeRecord, runtime_sha256: 'another executable' }, runtime, native));
  assert.throws(() => checkRuntime(nativeRecord, runtime, Buffer.from('changed executable')));
});

test('publication metadata cannot silently select another registry or repository', () => {
  assert.doesNotThrow(() => checkPackage(metadata, config));
  assert.throws(() => checkPackage({ ...metadata, private: true }, config));
  assert.throws(() => checkPackage({ ...metadata, publishConfig: { access: 'public', registry: 'https://example.invalid/' } }, config));
  assert.throws(() => checkPackage({ ...metadata, repository: { url: 'git+https://github.com/someone/fork.git' } }, config));
});
