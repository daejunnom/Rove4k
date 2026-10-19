import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, openSync } from 'node:fs';
import { chmod, mkdir, readFile, readdir, realpath, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { artifactRoot, packageRoot, platformKey, repositoryRoot } from '../npm/lib/paths.mjs';

export { artifactRoot, packageRoot, platformKey, repositoryRoot };
export const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export async function json(file) { return JSON.parse(await readFile(file, 'utf8')); }
export async function writeJson(file, value) { await mkdir(path.dirname(file), { recursive: true }); await writeFile(file, `${JSON.stringify(value, null, 2)}\n`); }

export function packedPackage(output, expected) {
  const value = JSON.parse(output);
  // npm 10/11 return an array; npm 12 keys results by package name.
  const records = Array.isArray(value) ? value
    : value && typeof value === 'object' && Object.keys(value).length === 1 && Object.hasOwn(value, expected.name)
      ? [value[expected.name]] : [];
  if (records.length !== 1) throw new Error('npm pack must report exactly one expected package.');
  const info = records[0];
  const filename = `${expected.name.replace(/^@/, '').replaceAll('/', '-')}-${expected.version}.tgz`;
  if (info?.name !== expected.name || info.version !== expected.version || info.filename !== filename) {
    throw new Error(`npm pack did not report ${expected.name}@${expected.version} as ${filename}.`);
  }
  if (!Array.isArray(info.files)) throw new Error('npm pack did not provide a file inventory.');
  return info;
}

export async function externalDirectory(directory) {
  const resolved = path.resolve(directory);
  let parent = resolved;
  const missing = [];
  for (;;) {
    try { parent = await realpath(parent); break; }
    catch (error) {
      if (error.code !== 'ENOENT') throw error;
      missing.unshift(path.basename(parent));
      const next = path.dirname(parent);
      if (next === parent) throw error;
      parent = next;
    }
  }
  const canonical = path.join(parent, ...missing);
  const repo = await realpath(repositoryRoot);
  if (canonical === repo || canonical.startsWith(`${repo}${path.sep}`)) throw new Error(`Native outputs must stay outside Rove4k: ${canonical}`);
  await mkdir(canonical, { recursive: true });
  return canonical;
}

export async function buildEnvironment() {
  const artifacts = await externalDirectory(artifactRoot());
  const target = await externalDirectory(process.env.CARGO_TARGET_DIR ?? path.join(artifacts, 'cargo-target'));
  return { artifacts, target, env: { ...process.env, CARGO_TARGET_DIR: target, CARGO_BUILD_JOBS: process.env.CARGO_BUILD_JOBS ?? '2' } };
}

export async function sourceFingerprint() {
  const names = ['Cargo.toml', 'Cargo.lock', 'tools/nvcompact/Cargo.toml'];
  async function visit(directory) {
    for (const entry of await readdir(path.join(repositoryRoot, directory), { withFileTypes: true })) {
      const name = `${directory}/${entry.name}`;
      if (entry.isSymbolicLink()) throw new Error(`Rust source symlinks require an explicit build contract: ${name}`);
      if (entry.isDirectory()) await visit(name);
      else if (entry.isFile()) names.push(name);
    }
  }
  await visit('tools/nvcompact/src');
  names.sort();
  const values = {};
  for (const name of names) values[name] = hash(await readFile(path.join(repositoryRoot, name)));
  return { files: values, sha256: hash(Buffer.from(JSON.stringify(values))) };
}

let sequence = 0;
export async function execute(command, args, options = {}) {
  const logs = options.logs ?? path.join(artifactRoot(), 'command-logs');
  await mkdir(logs, { recursive: true });
  const id = `${Date.now()}-${process.pid}-${sequence++}`;
  const stdoutPath = path.join(logs, `${id}.stdout`);
  const stderrPath = path.join(logs, `${id}.stderr`);
  const out = openSync(stdoutPath, 'wx');
  const err = openSync(stderrPath, 'wx');
  const started = Date.now();
  let child;
  let timeout;
  let force;
  let interrupted = false;
  const signalGroup = signal => {
    if (!child?.pid) return;
    try { process.kill(-child.pid, signal); } catch (error) { if (error.code !== 'ESRCH') throw error; }
  };
  const cancel = () => { interrupted = true; signalGroup('SIGTERM'); force ??= setTimeout(() => signalGroup('SIGKILL'), 1000); };
  let status;
  try {
    status = await new Promise((resolve, reject) => {
      child = spawn(command, args, { cwd: options.cwd ?? repositoryRoot, env: options.env ?? process.env,
        stdio: [options.input === undefined ? 'ignore' : 'pipe', out, err], detached: true, shell: false });
      child.once('error', reject);
      child.once('close', (code, signal) => resolve({ code, signal }));
      if (options.input !== undefined) child.stdin.end(options.input);
      timeout = setTimeout(cancel, options.seconds === undefined ? 600000 : options.seconds * 1000);
      process.on('SIGINT', cancel); process.on('SIGTERM', cancel);
    });
  } finally {
    clearTimeout(timeout); clearTimeout(force);
    process.removeListener('SIGINT', cancel); process.removeListener('SIGTERM', cancel);
    signalGroup('SIGKILL');
    closeSync(out); closeSync(err);
  }
  const cap = options.outputBytes ?? 16 << 20;
  if ((await stat(stdoutPath)).size + (await stat(stderrPath)).size > cap) throw new Error(`Command output exceeded ${cap} bytes; inspect ${logs}`);
  const stdout = await readFile(stdoutPath);
  const stderr = await readFile(stderrPath);
  const result = { command, args, ...status, interrupted, seconds: (Date.now() - started) / 1000,
    stdout, stderr, stdout_path: stdoutPath, stderr_path: stderrPath };
  if (!options.allowFailure && (status.code !== 0 || interrupted)) {
    throw new Error(`${command} failed (${status.code ?? status.signal}${interrupted ? ', interrupted' : ''}): ${stderr.toString('utf8').slice(-8192)}\nLogs: ${logs}`);
  }
  return result;
}

export async function copyOwnFile(source, destination, executable = false) {
  await mkdir(path.dirname(destination), { recursive: true });
  await writeFile(destination, await readFile(source));
  await chmod(destination, executable ? 0o755 : 0o644);
}
