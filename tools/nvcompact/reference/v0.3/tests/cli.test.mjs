import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, openSync, closeSync, readFileSync, rmSync } from 'node:fs';
import { mkdtemp, writeFile, readFile, mkdir, rm, symlink, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';

const root = fileURLToPath(new URL('../', import.meta.url));
const packageMetadata = JSON.parse(readFileSync(path.join(root, 'packages/nvcompact/package.json'), 'utf8'));
const cli = path.join(root, 'packages/nvcompact/bin/nvcompact.mjs');
const runtime = path.join(root, 'packages/nvcompact/python');
const cleanups = new Map();

function ownCleanup(directory, callback) {
  cleanups.get(directory).push(callback);
}

function start(executable, args, options = {}) {
  // Real file descriptors also work in sandboxes whose Node-to-Node pipe
  // transport drops asynchronous writes; the assertions still inspect all bytes.
  const capture = mkdtempSync(path.join(tmpdir(), 'nvcompact-cli-capture-'));
  const outPath = path.join(capture, 'stdout'), errPath = path.join(capture, 'stderr');
  const out = openSync(outPath, 'w'), err = openSync(errPath, 'w');
  const child = spawn(executable, args, {
    cwd: root, env: process.env, stdio: ['pipe', out, err], shell: false, ...options,
  });
  closeSync(out);
  closeSync(err);
  const completion = new Promise((resolve, reject) => {
    let failed = false;
    child.once('error', error => { failed = true; reject(error); });
    child.once('close', (code, signal) => {
      const result = { code, signal, stdout: readFileSync(outPath, 'utf8'), stderr: readFileSync(errPath, 'utf8') };
      rmSync(capture, { recursive: true, force: true });
      if (!failed) resolve(result);
    });
  });
  child.stdin.on('error', () => {});
  return { child, completion };
}

async function run(args, options = {}, input = '') {
  const task = start(process.execPath, [cli, ...args], options);
  task.child.stdin.end(input);
  return await task.completion;
}

async function temp(t) {
  const directory = await mkdtemp(path.join(tmpdir(), 'nvcompact-cli-'));
  cleanups.set(directory, []);
  t.after(async () => {
    try {
      for (const cleanup of cleanups.get(directory).reverse()) await cleanup();
    } finally {
      cleanups.delete(directory);
      await rm(directory, { recursive: true, force: true });
    }
  });
  return directory;
}

async function pythonPath() {
  const task = start(process.env.NVCOMPACT_PYTHON || 'python3', ['-c', 'import sys; print(sys.executable)']);
  task.child.stdin.end();
  const result = await task.completion;
  assert.equal(result.code, 0, result.stderr);
  return result.stdout.trim();
}

async function exists(file) {
  try { await access(file); return true; } catch { return false; }
}

test('help and version work without Python; every command exposes help', { timeout: 20000 }, async () => {
  const env = { ...process.env, NVCOMPACT_PYTHON: '/missing/nvcompact-python' };
  assert.equal((await run(['--help'], { env })).code, 0);
  const version = await run(['--version'], { env });
  assert.equal(version.code, 0);
  assert.equal(version.stdout, `${packageMetadata.version}\n`);
  for (const command of ['build', 'run', 'reproduce', 'notation', 'rewrite-c', 'envelope', 'uci', 'replay', 'engines', 'resource']) {
    const result = await run([command, '--help']);
    assert.equal(result.code, 0, `${command}: ${result.stderr}`);
    assert.match(result.stdout, /usage:/i);
  }
});

test('doctor exercises installed codec APIs through an executable path containing spaces', { timeout: 10000 }, async t => {
  const directory = await temp(t);
  const python = path.join(directory, 'python executable ; $literal');
  await symlink(await pythonPath(), python);
  const result = await run(['doctor', '--json'], { env: { ...process.env, NVCOMPACT_PYTHON: python } });
  assert.equal(result.code, 0, result.stderr);
  const data = JSON.parse(result.stdout);
  assert.equal(data.status, 'pass');
  assert.equal(data.implementation, 'CPython');
  assert.equal(data.checks.raw_lzma2_x86, 'pass');
  assert.equal(data.checks.bz2, 'pass');
  assert.match(data.adapter_sha256, /^[0-9a-f]{64}$/);
});

test('argv, cwd, stdin/stdout/stderr and a real nonzero child status survive the Node launch boundary', { timeout: 10000 }, async t => {
  const directory = await temp(t);
  const fake = path.join(directory, 'argument recorder with spaces');
  await writeFile(fake, `#!${process.execPath}\nimport fs from 'node:fs';\nprocess.stdout.write(JSON.stringify({argv:process.argv.slice(2),cwd:process.cwd(),stdin:fs.readFileSync(0,'utf8')}));\nprocess.stderr.write('fixture stderr\\n');\nprocess.exitCode=37;\n`, { mode: 0o755 });
  const special = ['notation', 'a file;$(touch INJECTED).cpp', '--output', 'quotes\'" and `touch INJECTED2` $HOME.cpp'];
  const result = await run(special, { cwd: directory, env: { ...process.env, NVCOMPACT_PYTHON: fake } }, 'literal stdin\n');
  assert.equal(result.code, 37);
  const observed = JSON.parse(result.stdout);
  assert.deepEqual(observed.argv, ['-B', path.join(runtime, 'nvlaunch.py'), ...special]);
  assert.equal(observed.cwd, directory);
  assert.equal(observed.stdin, 'literal stdin\n');
  assert.equal(result.stderr, 'fixture stderr\n');
  assert.equal(await exists(path.join(directory, 'INJECTED')), false);
  assert.equal(await exists(path.join(directory, 'INJECTED2')), false);
});

test('Python override errors are explicit and never trigger fallback or shell parsing', { timeout: 10000 }, async () => {
  const absent = await run(['doctor'], { env: { ...process.env, NVCOMPACT_PYTHON: '/missing/nvcompact-python' } });
  assert.equal(absent.code, 127);
  assert.match(absent.stderr, /could not launch/);
  const shellWords = await run(['doctor'], { env: { ...process.env, NVCOMPACT_PYTHON: 'python3 -I' } });
  assert.equal(shellWords.code, 127);
  const empty = await run(['doctor'], { env: { ...process.env, NVCOMPACT_PYTHON: '' } });
  assert.equal(empty.code, 2);
  assert.match(empty.stderr, /nonempty executable path/);
});

test('a real core error is preserved and does not create a success artifact', { timeout: 10000 }, async t => {
  const directory = await temp(t);
  const result = await run(['notation', 'absent.cpp', '--language', 'cpp', '--output', 'result.cpp'], { cwd: directory });
  assert.equal(result.code, 2);
  assert.match(result.stderr, /nvnotation:/);
  assert.equal(await exists(path.join(directory, 'result.cpp')), false);
});

test('engines rejects missing, nonexistent, empty and unknown selections before creating output', { timeout: 10000 }, async t => {
  const directory = await temp(t);
  const manifests = path.join(directory, 'manifests');
  await mkdir(manifests);
  for (const extra of [[], ['--manifests', 'absent'], ['--manifests', manifests]]) {
    const result = await run(['engines', ...extra, '--output', 'result'], { cwd: directory });
    assert.equal(result.code, 2, result.stderr);
    assert.equal(await exists(path.join(directory, 'result')), false);
  }
  await writeFile(path.join(manifests, 'present.json'), '{}');
  const result = await run(['engines', '--manifests', manifests, '--only', 'unknown', '--output', 'result'], { cwd: directory });
  assert.equal(result.code, 2);
  assert.match(result.stderr, /unknown engine names: unknown/);
  assert.equal(await exists(path.join(directory, 'result')), false);
});

async function waitUntil(predicate, task, milliseconds = 10000) {
  const deadline = Date.now() + milliseconds;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    if (task.child.exitCode !== null || task.child.signalCode !== null) {
      const result = await task.completion;
      throw new Error(`child exited before ready: ${JSON.stringify(result)}`);
    }
    await delay(25);
  }
  throw new Error('fixture did not become ready within its startup budget');
}

async function stopFixture(task) {
  if (task.child.exitCode === null && task.child.signalCode === null) task.child.kill('SIGTERM');
  await Promise.race([task.completion, delay(3000)]);
  if (task.child.exitCode === null && task.child.signalCode === null) task.child.kill('SIGKILL');
}

async function lifetimeObserver(directory, python, t) {
  // Every fixture process exclusively locks one file until it exits. A separate
  // Python probe checks the kernel lock, so this observes OS lifetime handles
  // without comparing PIDs across namespaces or using sockets/process scans.
  const lockDirectory = path.join(directory, 'lifetime');
  await mkdir(lockDirectory);
  ownCleanup(directory, async () => {
    await writeFile(path.join(lockDirectory, 'STOP'), 'test cleanup');
    await delay(100);
  });
  async function held(labels) {
    const code = `import fcntl,json,sys\nfrom pathlib import Path\nr={}\nfor label in sys.argv[2:]:\n with open(Path(sys.argv[1])/(label+'.lock'),'r+') as f:\n  try:\n   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\n   r[label]=False\n  except BlockingIOError:r[label]=True\nprint(json.dumps(r))\n`;
    const task = start(python, ['-c', code, lockDirectory, ...labels]);
    task.child.stdin.end();
    const result = await task.completion;
    assert.equal(result.code, 0, result.stderr);
    return JSON.parse(result.stdout);
  }
  return { lockDirectory, held,
    async ready(labels) { return (await Promise.all(labels.map(label => exists(path.join(lockDirectory, `${label}.lock`))))).every(Boolean); },
    async stopped(labels) {
      const deadline = Date.now() + 3000;
      let states;
      do {
        states = await held(labels);
        if (Object.values(states).every(value => !value)) break;
        await delay(25);
      } while (Date.now() < deadline);
      for (const label of labels) assert.equal(states[label], false, `fixture process ${label} still holds its lifetime lock`);
    } };
}

const controlCode = `import fcntl,sys,time\nfrom pathlib import Path\nroot=Path(sys.argv[1]);guard=open(root/(sys.argv[2]+'.lock'),'w');fcntl.flock(guard,fcntl.LOCK_EX)\nend=time.monotonic()+120\nwhile time.monotonic()<end and root.exists() and not (root/'STOP').exists():time.sleep(.05)\n`;

for (const [signal, nested] of [['SIGTERM', false], ['SIGINT', false], ['SIGTERM', true]]) {
  test(`real UCI cancellation ${signal}${nested ? ' through a nested core helper' : ''} stops engine and grandchild`, { timeout: 20000 }, async t => {
    const oracle = process.env.NVUCI_ORACLE_PATH;
    if (!oracle) { t.skip('set NVUCI_ORACLE_PATH to an installed development chess oracle to exercise real UCI cancellation'); return; }
    const directory = await temp(t);
    const python = await pythonPath();
    const observer = await lifetimeObserver(directory, python, t);
    const marker = path.join(directory, 'ready.json');
    const engine = path.join(directory, 'waiting engine.py');
    await writeFile(engine, `import fcntl,os,subprocess,sys,threading,time\nfrom pathlib import Path\nroot=Path(sys.argv[2]);guard=open(root/'engine.lock','w');fcntl.flock(guard,fcntl.LOCK_EX)\ndef monitor():\n end=time.monotonic()+120\n while time.monotonic()<end and not (root/'STOP').exists():time.sleep(.05)\n os._exit(0)\nthreading.Thread(target=monitor,daemon=True).start()\nchild=subprocess.Popen([sys.executable,'-c',${JSON.stringify(controlCode)},sys.argv[2],'grandchild'])\nfor line in sys.stdin:\n if line.strip()=='uci': print('id name lifecycle-fixture\\nuciok',flush=True)\n elif line.strip()=='isready':\n  print('readyok',flush=True)\n  Path(sys.argv[1]).write_text('ready')\n elif line.startswith('go'):\n  while True: time.sleep(1)\n elif line.strip()=='quit': break\n`);
    let command = [python, engine, marker, observer.lockDirectory];
    if (nested) command = [python, path.join(runtime, 'nvuci.py'), '--command', JSON.stringify(command), '--oracle-path', oracle, '--search-seconds', '30', '--max-seconds', '60'];
    const task = start(process.execPath, [cli, 'uci', '--command', JSON.stringify(command), '--oracle-path', oracle,
      '--startup-seconds', '20', '--search-seconds', '30', '--max-seconds', '60']);
    task.child.stdin.end();
    ownCleanup(directory, async () => stopFixture(task));
    await waitUntil(async () => (await exists(marker)) && (await observer.ready(['engine', 'grandchild'])), task);
    assert.deepEqual(await observer.held(['engine', 'grandchild']), { engine: true, grandchild: true });
    task.child.kill(signal);
    const result = await task.completion;
    assert.equal(result.code, signal === 'SIGINT' ? 130 : 143, result.stderr);
    assert.match(result.stderr, /owned process cleanup completed/);
    await observer.stopped(['engine', 'grandchild']);
  });
}

test('cancelling an active native portfolio stops worker groups and cancels queued work', { timeout: 20000 }, async t => {
  const directory = await temp(t);
  const python = await pythonPath();
  const observer = await lifetimeObserver(directory, python, t);
  const marker = path.join(directory, 'workers');
  await mkdir(marker);
  const source = `import fcntl,os,subprocess,sys,time\nfrom pathlib import Path\nmode=sys.argv[1]\nif mode=='compile':\n if sys.argv[3]!='v0':\n  root=Path(sys.argv[5]);guard=open(root/(sys.argv[3]+'-worker.lock'),'w');fcntl.flock(guard,fcntl.LOCK_EX)\n  child=subprocess.Popen([sys.executable,'-c',${JSON.stringify(controlCode)},sys.argv[5],sys.argv[3]+'-grandchild'])\n  Path(sys.argv[4],sys.argv[3]+'.json').write_text('ready')\n  end=time.monotonic()+120\n  while time.monotonic()<end and not (root/'STOP').exists():time.sleep(.05)\n  sys.exit(1)\n Path(sys.argv[2]).write_bytes(b'fixture object')\nelif mode=='link': Path(sys.argv[2]).write_bytes(Path('/bin/true').read_bytes())\n`;
  await writeFile(path.join(directory, 'worker.py'), source);
  const variants = Array.from({ length: 32 }, (_, i) => ({ id: `v${i}`, sources: ['worker.py'],
    commands: [['{python}', '{source}', 'compile', '{object}', `v${i}`, marker, observer.lockDirectory]] }));
  const manifest = {
    format: 1, project_root: '.', target: 'x86_64-unknown-linux-gnu',
    contract: 'Cancellation fixture only; no semantic compression claim.', inputs: ['worker.py'],
    tools: { python: { executable: python } },
    components: [{ id: 'worker', contract: 'Owned subprocess lifecycle fixture', variants }],
    build_profiles: [{ id: 'one', variables: {} }],
    link_profiles: [{ id: 'one', contract: 'Fixture link', argv: ['{python}', '{root}/worker.py', 'link', '{binary}'] }],
    baseline: { build: 'one', link: 'one', order: ['worker'], variants: { worker: 'v0' } },
    verify: ['{python}', '-c', 'print("fixture verification only")'],
    codecs: [], max_bytes: 100000, max_native_bytes: 100000,
  };
  await writeFile(path.join(directory, 'manifest.json'), JSON.stringify(manifest));
  const task = start(process.execPath, [cli, 'run', path.join(directory, 'manifest.json'), '--out', path.join(directory, 'run'),
    '--jobs', '2', '--command-seconds', '120', '--max-seconds', '240']);
  task.child.stdin.end();
  ownCleanup(directory, async () => stopFixture(task));
  const labels = ['v1-worker', 'v1-grandchild', 'v2-worker', 'v2-grandchild'];
  await waitUntil(async () => (await observer.ready(labels)) && (await exists(path.join(marker, 'v1.json'))) && (await exists(path.join(marker, 'v2.json'))), task);
  assert.ok(Object.values(await observer.held(labels)).every(Boolean));
  const before = Date.now();
  task.child.kill('SIGTERM');
  const result = await task.completion;
  assert.equal(result.code, 143, result.stderr);
  assert.ok(Date.now() - before < 5000, 'cancellation waited for long-running or queued work');
  await observer.stopped(['v1-worker', 'v1-grandchild', 'v2-worker', 'v2-grandchild']);
  assert.equal(await exists(path.join(marker, 'v31.json')), false);
  assert.equal(await exists(path.join(directory, 'run/winner')), false);
});
