import { spawn } from 'node:child_process';
import { access, readFile, stat } from 'node:fs/promises';
import { constants } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { artifactRoot, packageRoot, platformKey, repositoryRoot } from './paths.mjs';

async function executable(file) {
  try {
    return (await stat(file)).isFile() && await access(file, constants.X_OK).then(() => true);
  } catch { return false; }
}

export async function resolveExecutable(env = process.env, root = packageRoot) {
  if (process.platform !== 'linux') throw new Error('NVCompact currently requires Linux. Build and run it in a Linux environment.');
  if (env.NVCOMPACT_BIN !== undefined) {
    if (!env.NVCOMPACT_BIN.trim()) throw new Error('NVCOMPACT_BIN must name an executable.');
    // A bare name intentionally uses PATH; an explicit relative pathname uses
    // the caller's working directory. No shell expansion is performed.
    return env.NVCOMPACT_BIN;
  }
  const bundled = path.join(root, 'native', platformKey(), 'nvcompact');
  if (await executable(bundled)) return bundled;
  // This branch is only for the source workspace. Installed packages must have
  // their own native file or an explicit NVCOMPACT_BIN; no ancestor probing.
  const workspacePackage = path.join(repositoryRoot, 'tools/nvcompact/npm');
  if (path.resolve(root) === workspacePackage && await executable(path.join(workspacePackage, 'bin/nvcompact.mjs'))) {
    try {
      await access(path.join(repositoryRoot, 'tools/nvcompact/Cargo.toml'));
      const info = JSON.parse(await readFile(path.join(artifactRoot(env), 'build.json'), 'utf8'));
      if (info.platform_key === platformKey() && typeof info.binary === 'string' && await executable(info.binary)) return info.binary;
    } catch { /* Emit the actionable missing-build diagnostic below. */ }
  }
  throw new Error(`No ${platformKey()} Rust executable is available. In Rove4k run npm run build:nvcompact; for an external build set NVCOMPACT_BIN. Install a locally prepared tarball from npm run pack:nvcompact.`);
}

export async function runCli(args, options = {}) {
  const env = options.env ?? process.env;
  let binary;
  try { binary = await resolveExecutable(env); }
  catch (error) { process.stderr.write(`nvcompact: ${error.message}\n`); return 2; }
  return await new Promise(resolve => {
    let child;
    let settled = false;
    const handlers = new Map();
    const finish = code => {
      if (settled) return;
      settled = true;
      for (const [signal, handler] of handlers) process.removeListener(signal, handler);
      resolve(code);
    };
    try { child = spawn(binary, args, { cwd: options.cwd ?? process.cwd(), env, stdio: 'inherit', shell: false }); }
    catch (error) { process.stderr.write(`nvcompact: cannot start Rust executable ${JSON.stringify(binary)}: ${error.message}\n`); finish(2); return; }
    for (const signal of ['SIGINT', 'SIGTERM']) {
      const handler = () => { if (child.pid) child.kill(signal); };
      handlers.set(signal, handler);
      process.on(signal, handler);
    }
    child.once('error', error => {
      process.stderr.write(`nvcompact: cannot start Rust executable ${JSON.stringify(binary)}: ${error.message}\n`);
      finish(2);
    });
    child.once('close', (code, signal) => finish(code ?? 128 + (os.constants.signals[signal] ?? 1)));
  });
}
