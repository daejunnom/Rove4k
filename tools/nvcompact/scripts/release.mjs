import { spawn } from 'node:child_process';
import { appendFile, copyFile, mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { artifactRoot, execute, externalDirectory, hash, json, packageRoot, repositoryRoot, sourceFingerprint, writeJson } from './common.mjs';

const configPath = fileURLToPath(new URL('./release-config.json', import.meta.url));
const releaseInputs = ['Cargo.toml', 'Cargo.lock', 'LICENSE', 'package.json', 'package-lock.json',
  'tools/nvcompact/Cargo.toml', 'tools/nvcompact/src', 'tools/nvcompact/npm', 'tools/nvcompact/scripts',
  '.github/workflows/nvcompact-publish.yml'];

export function checkPackage(metadata, config) {
  if (metadata.name !== config.package || metadata.private === true
      || metadata.publishConfig?.access !== 'public'
      || metadata.publishConfig?.registry !== config.registry
      || metadata.repository?.url !== `git+https://github.com/${config.repository}.git`) {
    throw new Error('Package name, visibility, registry or repository disagrees with release-config.json.');
  }
  if (!/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(metadata.version)) {
    throw new Error('This release path requires a stable numeric version; design a prerelease dist-tag path explicitly.');
  }
}

export function checkCiRequest(env, config, version) {
  if (env.GITHUB_ACTIONS !== 'true' || env.GITHUB_EVENT_NAME !== 'workflow_dispatch'
      || env.GITHUB_REPOSITORY !== config.repository
      || env.GITHUB_REF !== `refs/heads/${config.release_branch}`
      || env.GITHUB_WORKFLOW_REF !== `${config.repository}/.github/workflows/${config.workflow}@refs/heads/${config.release_branch}`) {
    throw new Error('Releases require an explicit workflow_dispatch from the configured repository, main branch and workflow.');
  }
  if (env.NVC_RELEASE_VERSION !== version || !/^[0-9a-f]{40}$/.test(env.NVC_RELEASE_COMMIT ?? '')
      || env.NVC_RELEASE_COMMIT !== env.GITHUB_SHA) {
    throw new Error('Requested version and exact commit must match this workflow checkout.');
  }
  if (!['prepare', 'stage', 'publish'].includes(env.NVC_RELEASE_OPERATION)) {
    throw new Error('Select exactly one release operation: prepare, stage or publish.');
  }
  return env.NVC_RELEASE_OPERATION;
}

export function checkRegistryState(packument, config, version, requireExisting) {
  if (packument === null) {
    if (requireExisting) throw new Error('The package does not exist yet. Complete the first manual publish before configuring OIDC.');
    return;
  }
  if (packument.name !== config.package || !packument.maintainers?.some(owner => owner.name === config.npm_owner)) {
    throw new Error(`The registry package is not maintained by the configured npm owner ${config.npm_owner}.`);
  }
  if (Object.hasOwn(packument.versions ?? {}, version)) {
    throw new Error(`Version ${version} already exists. Published versions are immutable; select a new reviewed version.`);
  }
}

export function checkBundle(record, bytes, config, metadata) {
  checkPackage(metadata, config);
  if (record.format !== 'nvcompact.release.v1' || record.package !== metadata.name || record.version !== metadata.version
      || record.registry !== config.registry || record.npm_owner !== config.npm_owner || record.repository !== config.repository
      || record.dist_tag !== config.dist_tag || record.platform_key !== config.platform_key || record.rust_target !== config.rust_target
      || record.tarball !== `${metadata.name}-${metadata.version}.tgz`
      || record.bytes !== bytes.length || record.sha256 !== hash(bytes)
      || record.validation?.status !== 'pass' || record.validation?.package_sha256 !== record.sha256) {
    throw new Error('The release bundle disagrees with its verified tarball, target or publication configuration.');
  }
}

export function checkRuntime(record, runtime, bytes) {
  if (runtime.format !== 'nvcompact.npm-native.v1' || runtime.version !== record.version
      || runtime.platform_key !== record.platform_key || runtime.rust_host !== record.rust_target
      || runtime.source_sha256 !== record.source_sha256 || runtime.sha256 !== record.runtime_sha256
      || record.validation?.runtime_sha256 !== runtime.sha256 || runtime.bytes !== bytes.length
      || runtime.sha256 !== hash(bytes)) {
    throw new Error('The tarball runtime, its actual executable and the recorded source/target identity disagree.');
  }
}

export function publicationArgs(operation, tarball, config, ci) {
  if (!['stage', 'publish'].includes(operation)) throw new Error('Publication requires stage or publish.');
  return [...(operation === 'stage' ? ['stage', 'publish'] : ['publish']), tarball,
    '--access', 'public', '--registry', config.registry, '--tag', config.dist_tag,
    '--ignore-scripts', '--dry-run=false', '--force=false', ...(ci ? ['--provenance'] : [])];
}

async function gitState() {
  const commit = (await execute('git', ['rev-parse', 'HEAD'], { seconds: 15 })).stdout.toString('utf8').trim();
  const branch = (await execute('git', ['branch', '--show-current'], { seconds: 15 })).stdout.toString('utf8').trim();
  const changed = (await execute('git', ['status', '--porcelain', '--untracked-files=normal', '--', ...releaseInputs],
    { seconds: 15 })).stdout.toString('utf8');
  return { commit, branch, release_inputs_clean: changed.length === 0 };
}

async function workflowOutput(values) {
  if (!process.env.GITHUB_OUTPUT) return;
  for (const [key, value] of Object.entries(values)) {
    if (/[\r\n]/.test(String(value))) throw new Error(`Multiline GitHub output is not supported: ${key}`);
    await appendFile(process.env.GITHUB_OUTPUT, `${key}=${value}\n`);
  }
}

async function prepare(config, metadata, noBuild) {
  const before = await gitState();
  const scripts = [['pack.mjs', ...(noBuild ? ['--no-build'] : [])], ['verify-package.mjs']];
  for (const [script, ...args] of scripts) {
    const result = await execute(process.execPath, [fileURLToPath(new URL(script, import.meta.url)), ...args], { seconds: 1800 });
    process.stdout.write(result.stdout); process.stderr.write(result.stderr);
  }
  const artifacts = await externalDirectory(artifactRoot());
  const packed = await json(path.join(artifacts, 'package.json'));
  const validated = await json(path.join(artifacts, 'package-validation.json'));
  if (packed.name !== metadata.name || packed.version !== metadata.version || packed.private
      || validated.runtime_sha256 !== packed.runtime.sha256) {
    throw new Error('Prepared package identity or verified native runtime does not match the release.');
  }
  const state = await gitState();
  if (before.commit !== state.commit) throw new Error('The checkout changed commits while preparing the release.');
  const releases = path.join(artifacts, 'releases'); await mkdir(releases, { recursive: true });
  const bundle = await mkdtemp(path.join(releases, `${metadata.name}-${metadata.version}-`));
  const record = { format: 'nvcompact.release.v1', package: metadata.name, version: metadata.version,
    npm_owner: config.npm_owner, registry: config.registry, dist_tag: config.dist_tag, repository: config.repository,
    commit: state.commit, release_inputs_clean: before.release_inputs_clean && state.release_inputs_clean,
    source_sha256: (await sourceFingerprint()).sha256, platform_key: packed.platform_key,
    rust_target: packed.runtime.rust_host, runtime_sha256: packed.runtime.sha256,
    tarball: `${metadata.name}-${metadata.version}.tgz`, bytes: packed.bytes, sha256: packed.sha256,
    validation: { status: validated.status, package_sha256: validated.package_sha256,
      runtime_sha256: validated.runtime_sha256, checks: validated.checks }, published: false };
  const bytes = await readFile(packed.path); checkBundle(record, bytes, config, metadata);
  await copyFile(packed.path, path.join(bundle, record.tarball));
  await writeJson(path.join(bundle, 'release.json'), record);
  await writeJson(path.join(artifacts, 'release-latest.json'), { bundle });
  await workflowOutput({ bundle, package_sha256: record.sha256 });
  process.stdout.write(`${JSON.stringify({ status: 'prepared', bundle, ...record }, null, 2)}\n`);
}

async function registryPackage(config) {
  const response = await fetch(new URL(encodeURIComponent(config.package), config.registry), {
    headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(30000), redirect: 'error',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Registry lookup returned HTTP ${response.status}; no publication attempted.`);
  return await response.json();
}

async function interactive(command, args, env) {
  // npm owns login/2FA prompts; credentials are never command arguments or our log files.
  // This group is separate so cancellation includes npm's owned subprocesses.
  let child; let timer; let force; let interrupted = false;
  const signal = value => {
    if (!child?.pid) return;
    try { process.kill(-child.pid, value); } catch (error) { if (error.code !== 'ESRCH') throw error; }
  };
  const cancel = () => { interrupted = true; signal('SIGTERM'); force ??= setTimeout(() => signal('SIGKILL'), 1000); };
  let status;
  try {
    status = await new Promise((resolve, reject) => {
      child = spawn(command, args, { cwd: repositoryRoot, env, shell: false, detached: true, stdio: 'inherit' });
      child.once('error', reject); child.once('close', (code, receivedSignal) => resolve({ code, signal: receivedSignal }));
      timer = setTimeout(cancel, 15 * 60 * 1000);
      process.on('SIGINT', cancel); process.on('SIGTERM', cancel);
    });
  } finally {
    clearTimeout(timer); clearTimeout(force);
    process.removeListener('SIGINT', cancel); process.removeListener('SIGTERM', cancel); signal('SIGKILL');
  }
  if (interrupted || status.code !== 0) {
    throw new Error(`npm publication did not finish successfully (${status.code ?? status.signal}). Check the registry before retrying; a request may already have reached it.`);
  }
}

async function publish(config, metadata, bundleOption, start, ci) {
  const bundle = path.resolve(bundleOption ?? process.env.NVC_RELEASE_BUNDLE
    ?? (await json(path.join(artifactRoot(), 'release-latest.json'))).bundle);
  const record = await json(path.join(bundle, 'release.json'));
  if (record.tarball !== `${metadata.name}-${metadata.version}.tgz`) throw new Error('Unexpected tarball name in release bundle.');
  const tarball = path.join(bundle, record.tarball);
  checkBundle(record, await readFile(tarball), config, metadata);
  const manifest = await execute('tar', ['-xOf', tarball, 'package/package.json'], { seconds: 30, outputBytes: 1 << 20 });
  const packedMetadata = JSON.parse(manifest.stdout.toString('utf8'));
  checkPackage(packedMetadata, config);
  if (packedMetadata.version !== metadata.version) throw new Error('The tarball manifest version does not match the release.');
  const runtimeManifest = await execute('tar', ['-xOf', tarball, 'package/native/runtime.json'], { seconds: 30, outputBytes: 1 << 20 });
  const runtimeBytes = await execute('tar', ['-xOf', tarball, `package/native/${config.platform_key}/nvcompact`],
    { seconds: 30, outputBytes: 64 << 20 });
  checkRuntime(record, JSON.parse(runtimeManifest.stdout.toString('utf8')), runtimeBytes.stdout);
  const operation = ci ? checkCiRequest(process.env, config, metadata.version) : 'publish';
  if (operation === 'prepare') throw new Error('The prepare operation cannot invoke the publication job.');
  const plan = { operation, package: record.package, version: record.version, npm_owner: config.npm_owner,
    registry: config.registry, commit: record.commit, tarball, bytes: record.bytes, sha256: record.sha256,
    authentication: ci ? 'GitHub OIDC' : 'interactive npm account', npm_dry_run_on_start: false, published: false };
  if (!start) {
    process.stdout.write(`${JSON.stringify({ status: 'planned', ...plan, start_option: '--start' }, null, 2)}\n`);
    return;
  }
  const state = await gitState();
  if (!state.release_inputs_clean || !record.release_inputs_clean || record.commit !== state.commit
      || record.source_sha256 !== (await sourceFingerprint()).sha256
      || (!ci && state.branch !== config.release_branch) || (ci && state.commit !== process.env.GITHUB_SHA)) {
    throw new Error('Publish the prepared artifact from the same clean reviewed main commit; prepare it again after merging or changing inputs.');
  }
  const npm = process.env.NVCOMPACT_NPM ?? 'npm';
  const env = { ...process.env };
  if (ci) {
    if (!env.ACTIONS_ID_TOKEN_REQUEST_URL || !env.ACTIONS_ID_TOKEN_REQUEST_TOKEN || env.NODE_AUTH_TOKEN || env.NPM_TOKEN) {
      throw new Error('CI publishing requires GitHub OIDC and no configured npm publish token.');
    }
    const auth = await mkdtemp(path.join(await externalDirectory(artifactRoot()), 'oidc-config-'));
    for (const name of ['user.npmrc', 'global.npmrc']) await writeFile(path.join(auth, name), '', { mode: 0o600 });
    for (const key of Object.keys(env)) {
      if (['npm_config_userconfig', 'npm_config_globalconfig'].includes(key.toLowerCase())) delete env[key];
    }
    env.NPM_CONFIG_USERCONFIG = path.join(auth, 'user.npmrc');
    env.NPM_CONFIG_GLOBALCONFIG = path.join(auth, 'global.npmrc');
  } else {
    const who = await execute(npm, ['whoami', '--registry', config.registry], { seconds: 60 });
    if (who.stdout.toString('utf8').trim() !== config.npm_owner) {
      throw new Error(`The active npm account must be ${config.npm_owner}. Select that account with npm login before publishing.`);
    }
  }
  checkRegistryState(await registryPackage(config), config, metadata.version, ci);
  // Recheck the exact file after network/account checks; never repack during publication.
  checkBundle(record, await readFile(tarball), config, metadata);
  const args = publicationArgs(operation, tarball, config, ci);
  await interactive(npm, args, env);
  process.stdout.write(`${JSON.stringify({ ...plan, status: operation === 'stage' ? 'staged' : 'published',
    published: operation === 'publish' }, null, 2)}\n`);
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 0 || args.includes('--help')) {
    process.stdout.write('NVCompact release: prepare [--no-build]; publish [--bundle DIR] [--start]; check-ci; publish-ci --start [--bundle DIR].\nWithout --start, publish only prints its local plan.\n');
    return;
  }
  const [command, ...options] = args;
  const allowed = command === 'prepare' ? ['--no-build'] : ['publish', 'publish-ci'].includes(command) ? ['--start', '--bundle'] : [];
  let bundle; let start = false; let noBuild = false;
  for (let i = 0; i < options.length; i++) {
    if (!allowed.includes(options[i])) throw new Error(`Unknown option ${options[i]} for ${command}.`);
    if (options[i] === '--bundle') {
      bundle = options[++i]; if (!bundle || bundle.startsWith('--')) throw new Error('--bundle requires a directory.');
    } else if (options[i] === '--start') start = true;
    else noBuild = true;
  }
  const config = await json(configPath);
  const metadata = await json(path.join(packageRoot, 'package.json')); checkPackage(metadata, config);
  if (command === 'prepare') return await prepare(config, metadata, noBuild);
  if (command === 'publish' || command === 'publish-ci') return await publish(config, metadata, bundle, start, command === 'publish-ci');
  if (command === 'check-ci') {
    checkCiRequest(process.env, config, metadata.version);
    const state = await gitState();
    if (!state.release_inputs_clean || state.commit !== process.env.GITHUB_SHA) throw new Error('Release checkout must be clean and match the requested commit.');
    await workflowOutput({ environment: config.environment, npm_cli: config.npm_cli_version,
      artifact_name: `${metadata.name}-${metadata.version}-${state.commit}` });
    process.stdout.write(`${JSON.stringify({ status: 'accepted', operation: process.env.NVC_RELEASE_OPERATION,
      version: metadata.version, commit: state.commit, environment: config.environment }, null, 2)}\n`);
    return;
  }
  throw new Error(`Unknown release command: ${command}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}
