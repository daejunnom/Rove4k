import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { closeSync, openSync, readFileSync } from 'node:fs';
import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const cli = fileURLToPath(new URL('../bin/nvcompact.mjs', import.meta.url));
const temporary = await mkdtemp(path.join(os.tmpdir(), 'nvcompact-node-fixture-'));
const stub = path.join(temporary, 'owned tool stub.mjs');
await writeFile(stub, `#!/usr/bin/env node
if (process.argv[2] === 'wait') {
  process.on('SIGTERM', () => { process.stdout.write('terminated\\n'); process.exit(42); });
  process.stdout.write('ready\\n');
  setInterval(() => {}, 1000);
} else {
  process.stdout.write(JSON.stringify({args:process.argv.slice(2),cwd:process.cwd()}));
  process.stderr.write('diagnostic');
  process.exitCode = process.argv[2] === 'failure' ? 7 : 0;
}
`);
await chmod(stub, 0o755);

async function invoke(args, env = {}, options = {}) {
  const work = await mkdtemp(path.join(temporary, 'invocation-'));
  const stdoutPath = path.join(work, 'stdout'); const stderrPath = path.join(work, 'stderr');
  const out = openSync(stdoutPath, 'wx'); const err = openSync(stderrPath, 'wx');
  let child; let timeout; let ready; let timedOut = false; let cancelled = false;
  const killGroup = () => {
    if (child?.pid) {
      try { process.kill(-child.pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
    }
  };
  let status;
  try {
    status = await new Promise((resolve, reject) => {
      child = spawn(process.execPath, [cli, ...args], { cwd: temporary, env: { ...process.env, NVCOMPACT_BIN: stub, ...env },
        detached: true, stdio: ['ignore', out, err] });
      timeout = setTimeout(() => { timedOut = true; killGroup(); }, 5000);
      if (options.cancel) ready = setInterval(() => {
        if (!cancelled && readFileSync(stdoutPath, 'utf8').includes('ready\n')) { cancelled = true; child.kill('SIGTERM'); }
      }, 20);
      child.once('error', reject);
      child.once('close', (code, signal) => resolve({ code, signal }));
    });
  } finally {
    clearTimeout(timeout); clearInterval(ready); killGroup(); closeSync(out); closeSync(err);
  }
  assert(!timedOut, `wrapper fixture timeout; logs: ${work}`);
  return { ...status, stdout: await readFile(stdoutPath, 'utf8'), stderr: await readFile(stderrPath, 'utf8') };
}

test('explicit binary receives literal argv and caller cwd', async () => {
  const args = ['notation', '한글 with spaces.c', '$literal', '`literal`', '--compiler-arg=-DVALUE={a,b}'];
  const result = await invoke(args);
  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), { args, cwd: temporary });
  assert.equal(result.stderr, 'diagnostic');
});

test('child exit status is retained', async () => {
  assert.equal((await invoke(['failure'])).code, 7);
});

test('missing explicit binary fails without a backend fallback', async () => {
  const result = await invoke(['doctor'], { NVCOMPACT_BIN: path.join(temporary, 'absent') });
  assert.equal(result.code, 2);
  assert.match(result.stderr, /cannot start Rust executable/);
});

test('termination reaches the owned child and its exit is awaited', async () => {
  const result = await invoke(['wait'], {}, { cancel: true });
  assert.equal(result.code, 42);
  assert.equal(result.stdout, 'ready\nterminated\n');
});

test('npm package remains private and contains no Python backend', async () => {
  const metadata = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
  assert.equal(metadata.private, true);
  assert.equal(metadata.name, '@rove4k/nvcompact');
  assert.deepEqual(metadata.bin, { nvcompact: 'bin/nvcompact.mjs' });
  assert(!metadata.files.some(name => /python|reference|vendor|inputs/.test(name)));
});

test.after(async () => { await rm(temporary, { recursive: true }); });
