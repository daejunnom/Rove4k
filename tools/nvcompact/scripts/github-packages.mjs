import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { appendFile, lstat, mkdir, mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { artifactRoot, externalDirectory, hash, json, packedPackage, repositoryRoot, sourceFingerprint, writeJson } from './common.mjs';
import { checkCiRequest } from './release.mjs';

export const registry = 'https://npm.pkg.github.com/';
export const workflow = 'nvcompact-github-packages.yml';
const exec = promisify(execFile);
const entries = ['LICENSE', 'README.md', 'package.json', 'bin/nvcompact.mjs', 'lib/cli.mjs',
  'lib/ensure-native.mjs', 'lib/paths.mjs', 'native/runtime.json', 'native/linux-x64/nvcompact'];

export function scopedName(config) {
  return '@' + config.repository.split('/')[0].toLowerCase() + '/' + config.package;
}

export function mirrorMetadata(source, config, version) {
  assert.equal(source.name, config.package, 'unexpected source package');
  assert.equal(source.version, version, 'unexpected source version');
  assert.equal(source.repository?.url, 'git+https://github.com/' + config.repository + '.git', 'unexpected source repository');
  assert.equal(source.publishConfig?.registry, config.registry, 'unexpected source registry');
  assert.notEqual(source.private, true, 'source package must be published');
  return { ...source, name: scopedName(config), publishConfig: { ...source.publishConfig, registry } };
}

export function checkSourceBytes(bytes, expected, integrity) {
  assert.match(expected, /^[a-f0-9]{64}$/, 'explicit npm tarball SHA-256 required');
  assert.equal(hash(bytes), expected, 'npm tarball SHA-256 differs from the reviewed release');
  assert.equal('sha512-' + createHash('sha512').update(bytes).digest('base64'), integrity, 'npm registry integrity mismatch');
}

export function checkArchivePaths(names) {
  assert.deepEqual([...names].sort(), entries.map(name => 'package/' + name).sort(),
    'archive must contain exactly the reviewed NVCompact package files');
}

export function checkInventory(original, mirrored, expectedManifest) {
  assert.deepEqual(Object.keys(mirrored).sort(), Object.keys(original).sort(), 'package file set changed');
  for (const name of Object.keys(original)) {
    if (name !== 'package.json') assert.deepEqual(mirrored[name], original[name], 'package content changed: ' + name);
  }
  assert.equal(mirrored['package.json'].sha256, hash(Buffer.from(JSON.stringify(expectedManifest, null, 2) + '\n')),
    'only the reviewed scoped manifest may replace package.json');
}

export function checkRequest(env, config, version) {
  return checkCiRequest(env, { ...config, workflow }, version);
}

export function registryMetadata(output, expected) {
  const value = JSON.parse(output);
  const records = Array.isArray(value) ? value : [value];
  assert.equal(records.length, 1, 'registry view must report exactly one version');
  const record = records[0];
  assert.equal(record?.name, expected.name, 'unexpected registry package');
  assert.equal(record.version, expected.version, 'unexpected registry version');
  assert.equal(record.repository?.url, 'git+https://github.com/' + expected.repository + '.git', 'unexpected registry repository');
  return record;
}

async function committedSourceFingerprint() {
  const names = Object.keys((await sourceFingerprint()).files);
  await run('git', ['diff', '--quiet', 'HEAD', '--', ...names]);
  const files = {};
  for (const name of names) {
    const blob = await run('git', ['show', 'HEAD:' + name]);
    files[name] = hash(Buffer.from(blob.stdout, 'utf8'));
  }
  // The released Linux build hashes Git's source bytes, not Windows checkout CRLF.
  return hash(Buffer.from(JSON.stringify(files)));
}

async function run(command, args, options = {}) {
  try {
    const result = await exec(command, args, { cwd: options.cwd ?? repositoryRoot, encoding: 'utf8',
      windowsHide: true, timeout: 180000, maxBuffer: 16 << 20, ...options });
    return { ...result, code: 0 };
  } catch (error) {
    if (!options.allowFailure) throw error;
    return { stdout: error.stdout ?? '', stderr: error.stderr ?? '', code: error.code };
  }
}

async function npm(args, cwd, allowFailure = false) {
  assert(process.env.npm_execpath, 'invoke through the documented npm run command');
  return run(process.execPath, [process.env.npm_execpath, ...args], { cwd, allowFailure });
}

async function inventory(directory, prefix = '') {
  const result = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const name = prefix + entry.name;
    const file = path.join(directory, entry.name);
    assert(!entry.isSymbolicLink(), 'package symlinks are not supported');
    if (entry.isDirectory()) Object.assign(result, await inventory(file, name + '/'));
    else {
      const info = await lstat(file);
      assert(info.isFile(), 'package entries must be regular files');
      const bytes = await readFile(file);
      result[name] = { bytes: bytes.length, sha256: hash(bytes),
        ...(process.platform === 'linux' ? { mode: info.mode & 0o777 } : {}) };
    }
  }
  return result;
}

async function unpack(tarball, destination) {
  const listed = await run('tar', ['-tzf', tarball]);
  checkArchivePaths(listed.stdout.trim().split(/\r?\n/));
  await mkdir(destination);
  await run('tar', ['-xzf', tarball, '-C', destination]);
  return path.join(destination, 'package');
}

async function installAndCheck(spec, directory, name, version, runtimeHash, online = false) {
  await mkdir(directory);
  await writeJson(path.join(directory, 'package.json'), { name: 'nvcompact-github-consumer', private: true, version: '1.0.0' });
  await npm(['install', spec, '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false',
    '--cache', path.join(directory, 'npm-cache'), ...(online ? ['--registry', registry] : ['--offline'])], directory);
  const installed = path.join(directory, 'node_modules', ...name.split('/'));
  assert.equal((await json(path.join(installed, 'package.json'))).name, name);
  assert.equal(hash(await readFile(path.join(installed, 'native/linux-x64/nvcompact'))), runtimeHash);
  const cli = path.join(installed, 'bin/nvcompact.mjs');
  const env = { ...process.env };
  delete env.NVCOMPACT_BIN; delete env.NVCOMPACT_ARTIFACT_DIR; delete env.NODE_AUTH_TOKEN;
  assert.equal((await run(process.execPath, [cli, '--version'], { cwd: directory, env })).stdout.trim(), 'nvcompact ' + version);
  const doctor = JSON.parse((await run(process.execPath, [cli, 'doctor', '--json'], { cwd: directory, env })).stdout);
  assert.equal(doctor.runtime, 'Rust');
  assert.equal(doctor.python_backend, false);
  assert.equal(doctor.targets_started, false);
}

async function prepare(config, version, expected) {
  assert.match(version, /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/);
  assert.match(expected ?? '', /^[a-f0-9]{64}$/, 'set NVC_NPM_TARBALL_SHA256 to the reviewed npm tarball SHA-256');
  const url = config.registry + config.package + '/' + version;
  const response = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(30000) });
  assert.equal(response.status, 200, 'the exact source version must already be published on npm');
  const metadata = await response.json();
  const canonicalTarball = config.registry + config.package + '/-/' + config.package + '-' + version + '.tgz';
  assert.equal(metadata.dist?.tarball, canonicalTarball, 'unexpected npm download host or path');
  const downloaded = await fetch(canonicalTarball, { redirect: 'error', signal: AbortSignal.timeout(60000) });
  assert.equal(downloaded.status, 200);
  const bytes = Buffer.from(await downloaded.arrayBuffer());
  assert(bytes.length < (64 << 20), 'source package exceeds this mirror workload');
  checkSourceBytes(bytes, expected, metadata.dist.integrity);
  const parent = await externalDirectory(path.join(artifactRoot(), 'github-packages'));
  const bundle = await mkdtemp(path.join(parent, version + '-'));
  const sourceTarball = path.join(bundle, 'source.tgz');
  await writeFile(sourceTarball, bytes);
  const source = await unpack(sourceTarball, path.join(bundle, 'source'));
  const sourceManifest = await json(path.join(source, 'package.json'));
  const manifest = mirrorMetadata(sourceManifest, config, version);
  const runtime = await json(path.join(source, 'native/runtime.json'));
  assert.equal(runtime.version, version);
  assert.equal(runtime.platform_key, config.platform_key);
  assert.equal(runtime.rust_host, config.rust_target);
  assert.equal(runtime.source_sha256, await committedSourceFingerprint(), 'npm native source differs from this reviewed checkout');
  const native = await readFile(path.join(source, 'native/linux-x64/nvcompact'));
  assert.equal(hash(native), runtime.sha256);
  assert.equal(native.length, runtime.bytes);
  const original = await inventory(source);
  await writeJson(path.join(source, 'package.json'), manifest);
  const packed = await npm(['pack', source, '--ignore-scripts', '--json', '--pack-destination', bundle], bundle);
  const info = packedPackage(packed.stdout, manifest);
  const tarball = path.join(bundle, info.filename);
  const target = await unpack(tarball, path.join(bundle, 'target'));
  const files = await inventory(target);
  checkInventory(original, files, manifest);
  const linux = process.platform === 'linux' && process.arch === 'x64';
  if (linux) await installAndCheck(tarball, path.join(bundle, 'local-consumer'), manifest.name, version, runtime.sha256);
  const record = { format: 'nvcompact.github-packages.v1', name: manifest.name, version, registry,
    repository: config.repository, workflow_commit: (await run('git', ['rev-parse', 'HEAD'])).stdout.trim(),
    source: { name: sourceManifest.name, url: canonicalTarball, sha256: expected,
      integrity: metadata.dist.integrity, runtime_sha256: runtime.sha256, source_sha256: runtime.source_sha256 },
    tarball: info.filename, sha256: hash(await readFile(tarball)), bytes: (await readFile(tarball)).length,
    files, local_install_validation: linux ? 'pass' : 'not_run_requires_linux_x64', published: false };
  await writeJson(path.join(bundle, 'mirror.json'), record);
  await writeJson(path.join(parent, 'latest.json'), { bundle });
  if (process.env.GITHUB_OUTPUT) await appendFile(process.env.GITHUB_OUTPUT, 'bundle=' + bundle + '\n');
  console.log(JSON.stringify({ status: 'prepared', bundle, ...record }, null, 2));
}

async function publish(config, version, start) {
  const { bundle } = await json(path.join(artifactRoot(), 'github-packages/latest.json'));
  const record = await json(path.join(bundle, 'mirror.json'));
  assert.equal(record.name, scopedName(config));
  assert.equal(record.version, version);
  assert.equal(record.registry, registry);
  assert.equal(record.repository, config.repository);
  assert.equal(record.source.sha256, process.env.NVC_NPM_TARBALL_SHA256);
  assert.equal(record.source.source_sha256, await committedSourceFingerprint());
  const tarball = path.join(bundle, record.tarball);
  assert.equal(record.tarball, record.name.slice(1).replace('/', '-') + '-' + version + '.tgz');
  assert.equal(hash(await readFile(tarball)), record.sha256, 'prepared tarball changed');
  if (!start) { console.log(JSON.stringify({ status: 'planned', ...record }, null, 2)); return; }
  assert.equal(process.platform, 'linux');
  assert.equal(record.local_install_validation, 'pass');
  assert.equal(checkRequest(process.env, config, version), 'publish');
  assert.equal((await run('git', ['rev-parse', 'HEAD'])).stdout.trim(), record.workflow_commit);
  assert.equal(record.workflow_commit, process.env.GITHUB_SHA);
  assert.equal((await run('git', ['status', '--porcelain', '--untracked-files=normal'])).stdout, '', 'publication checkout must remain clean');
  const spec = record.name + '@' + version;
  const before = await npm(['view', spec, '--json', '--registry', registry], bundle, true);
  let alreadyExists = false;
  if (before.code === 0) { registryMetadata(before.stdout, record); alreadyExists = true; }
  else {
    const failure = JSON.parse(before.stdout);
    assert.equal(failure.error?.code, 'E404', 'only a confirmed missing version can be published');
  }
  if (!alreadyExists) {
    const result = await npm(['publish', tarball, '--registry', registry, '--access', 'public', '--tag', config.dist_tag,
      '--ignore-scripts', '--dry-run=false', '--force=false', '--provenance=false'], bundle);
    process.stdout.write(result.stdout);
  }
  const remote = registryMetadata((await npm(['view', spec, '--json', '--registry', registry], bundle)).stdout, record);
  const downloaded = path.join(bundle, 'registry-download'); await mkdir(downloaded);
  const packed = packedPackage((await npm(['pack', spec, '--registry', registry, '--ignore-scripts',
    '--json', '--pack-destination', downloaded], bundle)).stdout, record);
  const registeredTarball = path.join(downloaded, packed.filename);
  const registered = await unpack(registeredTarball, path.join(bundle, 'registered'));
  assert.deepEqual(await inventory(registered), record.files, 'registered package differs from the verified mirror');
  await installAndCheck(spec, path.join(bundle, 'registry-consumer'), record.name, version, record.source.runtime_sha256, true);
  const result = { ...record, status: alreadyExists ? 'existing_version_verified' : 'published_and_registry_install_verified',
    published: true, registry_tarball_sha256: hash(await readFile(registeredTarball)), registry_integrity: remote.dist?.integrity,
    registry_install_validation: 'pass', visibility: 'check_package_settings_separately', observed_at: new Date().toISOString() };
  await writeJson(path.join(bundle, 'publication.json'), result);
  console.log(JSON.stringify(result, null, 2));
}

export async function main(args = process.argv.slice(2)) {
  const config = await json(new URL('./release-config.json', import.meta.url));
  const metadata = await json(new URL('../npm/package.json', import.meta.url));
  const version = process.env.NVC_RELEASE_VERSION ?? metadata.version;
  assert.equal(version, metadata.version, 'requested version must match the reviewed source package');
  if (args[0] === 'check-ci') { console.log(checkRequest(process.env, config, version)); return; }
  if (args[0] === 'prepare') return prepare(config, version, process.env.NVC_NPM_TARBALL_SHA256);
  if (args[0] === 'publish') return publish(config, version, args.includes('--start'));
  throw new Error('Use prepare, publish [--start], or check-ci through npm run.');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
