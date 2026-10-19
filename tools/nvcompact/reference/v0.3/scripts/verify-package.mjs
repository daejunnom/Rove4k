#!/usr/bin/env node
/** Install the actual local tarball outside the repository and exercise it.
 * No registry downloads or install hooks are used. This is packaging evidence,
 * not another TCEC campaign or a cross-platform compatibility claim.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, mkdirSync, mkdtempSync,
  readdirSync, lstatSync, realpathSync, rmSync, copyFileSync, cpSync, openSync, closeSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { gunzipSync } from 'node:zlib';

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const digest = data => createHash('sha256').update(data).digest('hex');
const json = path => JSON.parse(readFileSync(path, 'utf8'));

/** Bounded subprocess capture without a shell or synchronous child runner. */
export function captureProcess(executable, argv, options = {}) {
  return new Promise(resolveResult => {
    const outputRoot = mkdtempSync(join(tmpdir(), 'nvcompact command capture '));
    const outPath = join(outputRoot, 'stdout'), errPath = join(outputRoot, 'stderr');
    const out = openSync(outPath, 'wx'), err = openSync(errPath, 'wx');
    const child = spawn(executable, argv, { cwd: options.cwd, env: options.env,
      shell: false, stdio: ['ignore', out, err] });
    let failure, escalation;
    const maximum = options.maxBuffer ?? 8 * 1024 * 1024;
    function stop(error) {
      if (!failure) failure = error;
      child.kill('SIGTERM');
      if (!escalation) escalation = setTimeout(() => child.kill('SIGKILL'), 2000);
    }
    const timeout = setTimeout(() => stop(new Error(`command timeout after ${options.timeout ?? 30000} ms`)),
      options.timeout ?? 30000);
    const outputLimit = setInterval(() => {
      if (statSync(outPath).size + statSync(errPath).size > maximum) {
        stop(new Error(`command output exceeded ${maximum} bytes`));
      }
    }, 25);
    child.on('error', error => { failure ??= error; });
    child.on('close', (status, signal) => {
      clearTimeout(timeout);
      clearTimeout(escalation);
      clearInterval(outputLimit);
      const size = statSync(outPath).size + statSync(errPath).size;
      if (size > maximum) failure ??= new Error(`command output exceeded ${maximum} bytes`);
      const stdout = readFileSync(outPath).subarray(0, maximum).toString('utf8');
      const stderr = readFileSync(errPath).subarray(0, maximum).toString('utf8');
      closeSync(out); closeSync(err);
      rmSync(outputRoot, { recursive: true });
      resolveResult({ status, signal, stdout, stderr, ...(failure ? { error: failure } : {}) });
    });
  });
}

function field(block, offset, length) {
  return block.subarray(offset, offset + length).toString('utf8').replace(/\0.*$/s, '');
}

function paxRecords(data) {
  const result = {};
  for (let offset = 0; offset < data.length;) {
    const space = data.indexOf(32, offset);
    assert(space > offset, 'invalid PAX record length');
    const length = Number(data.subarray(offset, space).toString('ascii'));
    assert(Number.isSafeInteger(length) && length > space - offset + 2
      && offset + length <= data.length, 'invalid PAX record extent');
    const record = data.subarray(space + 1, offset + length - 1).toString('utf8');
    const equal = record.indexOf('=');
    assert(equal > 0, 'invalid PAX record');
    result[record.slice(0, equal)] = record.slice(equal + 1);
    offset += length;
  }
  return result;
}

/** Read the actual gzip/tar bytes, including npm's optional PAX path records. */
export function inspectTarball(path) {
  const compressed = readFileSync(path);
  const tar = gunzipSync(compressed, { maxOutputLength: 64 * 1024 * 1024 });
  const members = [];
  let next = {}, global = {}, longName;
  for (let offset = 0; offset + 512 <= tar.length;) {
    const block = tar.subarray(offset, offset + 512);
    if (block.every(byte => byte === 0)) break;
    const checksum = parseInt(field(block, 148, 8).trim(), 8);
    const observed = block.reduce((sum, byte, i) => sum + (i >= 148 && i < 156 ? 32 : byte), 0);
    assert.equal(observed, checksum, 'tar header checksum mismatch');
    const type = field(block, 156, 1) || '0';
    let name = field(block, 0, 100);
    const prefix = field(block, 345, 155);
    if (prefix) name = `${prefix}/${name}`;
    let size = parseInt(field(block, 124, 12).trim() || '0', 8);
    const attributes = { ...global, ...next };
    if (!['x', 'g', 'L', 'K'].includes(type)) {
      name = attributes.path ?? longName ?? name;
      if (attributes.size !== undefined) size = Number(attributes.size);
    }
    assert(Number.isSafeInteger(size) && size >= 0, 'invalid tar member size');
    assert(offset + 512 + size <= tar.length, 'truncated tar member');
    const data = tar.subarray(offset + 512, offset + 512 + size);
    offset += 512 + Math.ceil(size / 512) * 512;
    if (type === 'x') { next = paxRecords(data); continue; }
    if (type === 'g') { global = { ...global, ...paxRecords(data) }; continue; }
    if (type === 'L') { longName = data.toString('utf8').replace(/\0.*$/s, ''); continue; }
    assert.notEqual(type, 'K', 'package should not contain GNU long links');
    members.push({ name, type, bytes: size,
      mode: parseInt(field(block, 100, 8).trim() || '0', 8), sha256: digest(data), data });
    next = {};
    longName = undefined;
  }
  assert(members.length > 0, 'empty npm tarball');
  return { bytes: compressed.length, sha256: digest(compressed), members };
}

/** The distribution is a self-contained CLI; research inputs stay in the lab. */
export function validatePackageScope(archive) {
  const members = archive.members;
  const names = new Set();
  for (const member of members) {
    assert(member.name.startsWith('package/'), `member outside npm package: ${member.name}`);
    const parts = member.name.split('/');
    assert(!parts.includes('..') && !parts.includes('.'), `noncanonical member: ${member.name}`);
    assert(!names.has(member.name), `duplicate tar member: ${member.name}`);
    names.add(member.name);
    assert(['0', '5'].includes(member.type), `unexpected package link or special file: ${member.name}`);
    assert(!parts.some(part => ['vendor', 'inputs', 'evidence', 'node_modules', '__pycache__',
      '.git', '.deps', 'tcec4k-lab'].includes(part)), `research/build input leaked: ${member.name}`);
    assert(!/\.(?:pyc|pyo|tgz|zip)$/.test(member.name), `generated artifact leaked: ${member.name}`);
  }
  const manifestMember = members.find(member => member.name === 'package/package.json');
  assert(manifestMember, 'package manifest missing');
  const manifest = JSON.parse(manifestMember.data.toString('utf8'));
  assert.equal(manifest.name, 'nvcompact');
  assert.equal(typeof manifest.version, 'string');
  assert.equal(Object.keys(manifest.dependencies ?? {}).length, 0, 'CLI must install without registry dependencies');
  assert.equal(Object.keys(manifest.optionalDependencies ?? {}).length, 0);
  for (const hook of ['preinstall', 'install', 'postinstall']) {
    assert(!manifest.scripts?.[hook], `installation must not run ${hook}`);
  }
  const entry = typeof manifest.bin === 'string' ? manifest.bin : manifest.bin?.nvcompact;
  assert(entry, 'nvcompact bin entry missing');
  const bin = members.find(member => member.name === `package/${entry.replace(/^\.\//, '')}`);
  assert(bin && bin.type === '0', 'bin entry missing from actual tarball');
  assert(bin.data.toString('utf8').startsWith('#!/usr/bin/env node\n'), 'bin needs a Node shebang');
  assert(bin.mode & 0o111, 'bin must be executable');
  for (const required of ['nvcompact.py', 'nvpack.py', 'nvelf.py', 'nvnotation.py',
    'nvenvelope.py', 'nvuci.py', 'nvreproduce.py', 'run_engines.py', 'nvlaunch.py', 'nvresource.py', 'nvcflow.py']) {
    assert(names.has(`package/python/${required}`), `required runtime module missing: ${required}`);
  }
  for (const required of ['examples/mixed/manifest-notation.json', 'examples/mixed/verifier.py',
    'examples/native-build/manifest.json', 'examples/native-build/main.c',
    'examples/native-build/square_mul.c', 'examples/native-build/square_sum.c',
    'examples/native-build/verify.py',
    'linker/linux-x86_64-compact.ld', 'profiles/protocol-15s.json', 'README.md', 'NOTICE.md']) {
    assert(names.has(`package/${required}`), `documented asset missing: ${required}`);
  }
  return { manifest, entry, files: members.filter(member => member.type === '0').length };
}

function inventory(root) {
  const result = {};
  function visit(directory) {
    for (const name of readdirSync(directory).sort()) {
      const path = join(directory, name), stat = lstatSync(path), key = relative(root, path);
      if (stat.isDirectory()) visit(path);
      else {
        assert(stat.isFile(), `unexpected installed package entry: ${key}`);
        result[key] = { bytes: stat.size, mode: stat.mode & 0o777, sha256: digest(readFileSync(path)) };
      }
    }
  }
  visit(root);
  return result;
}

export async function verifyPackage(tarball = resolve(repository, `dist/nvcompact-${JSON.parse(readFileSync(join(repository, 'packages/nvcompact/package.json'), 'utf8')).version}.tgz`)) {
  tarball = resolve(tarball);
  const archive = inspectTarball(tarball), scope = validatePackageScope(archive);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const logs = join(repository, 'evidence/package-validation-runs', `${stamp}-${process.pid}`);
  mkdirSync(logs, { recursive: true });
  const temporary = mkdtempSync(join(tmpdir(), 'nvcompact package 한글 '));
  const consumer = join(temporary, 'consumer with spaces');
  mkdirSync(consumer);
  const cleanConfig = join(temporary, 'empty.npmrc');
  writeFileSync(cleanConfig, '');
  const environment = { ...process.env, npm_config_userconfig: cleanConfig,
    npm_config_cache: join(temporary, 'npm cache'), npm_config_offline: 'true',
    npm_config_audit: 'false', npm_config_fund: 'false' };
  const report = { format: 'nvcompact.package-validation.v1', status: 'running',
    package: { name: scope.manifest.name, version: scope.manifest.version,
      tarball: relative(repository, tarball), bytes: archive.bytes, sha256: archive.sha256,
      files: scope.files, scope: 'actual tar member inspection; research inputs excluded' },
    environment: { node: process.version, platform: process.platform, architecture: process.arch },
    commands: [], checks: [],
    limits: ['Linux host integration; no Windows/macOS execution claim.',
      'C-only installed examples; no new Rust or TCEC engine campaign.',
      'Lifecycle cancellation fixtures are tested separately by the CLI test suite.'] };
  const recordCheck = (name, details = {}) => report.checks.push({ name, status: 'pass', ...details });

  async function run(name, executable, argv, options = {}) {
    const started = performance.now();
    const result = await captureProcess(executable, argv, { cwd: options.cwd ?? consumer,
      env: { ...environment, ...options.env },
      timeout: options.timeout ?? 30000, maxBuffer: 8 * 1024 * 1024 });
    const stdoutPath = join(logs, `${name}.stdout`), stderrPath = join(logs, `${name}.stderr`);
    writeFileSync(stdoutPath, result.stdout ?? '');
    writeFileSync(stderrPath, result.stderr ?? '');
    const record = { name, argv: [executable, ...argv], exit_code: result.status,
      signal: result.signal, seconds: Number(((performance.now() - started) / 1000).toFixed(3)),
      stdout: relative(repository, stdoutPath), stderr: relative(repository, stderrPath),
      ...(result.error ? { error: result.error.message } : {}) };
    report.commands.push(record);
    if (options.failure) {
      assert(!result.error, `${name}: could not exercise intentional child failure: ${result.error}`);
      assert.notEqual(result.status, 0, `${name}: failure was changed into success`);
      assert(result.stderr?.length, `${name}: missing failure diagnostic`);
    } else {
      assert.equal(result.error, undefined, `${name}: ${result.error?.message}`);
      assert.equal(result.status, 0, `${name}: ${result.stderr?.slice(-2500)}`);
    }
    return result;
  }

  try {
    writeFileSync(join(consumer, 'package.json'), JSON.stringify({ name: 'nvcompact-install-probe', private: true }));
    await run('npm-version', 'npm', ['--version']);
    await run('offline-install', 'npm', ['install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund',
      '--package-lock=false', '--save=false', tarball], { timeout: 60000 });
    const installed = join(consumer, 'node_modules/nvcompact');
    const command = join(consumer, 'node_modules/.bin/nvcompact');
    assert.equal(realpathSync(command), realpathSync(join(installed, scope.entry)));
    assert(!realpathSync(installed).startsWith(repository + '/'), 'installed package still points into repository');
    const before = inventory(installed);
    for (const member of archive.members.filter(member => member.type === '0')) {
      const key = member.name.slice('package/'.length);
      assert.equal(before[key]?.sha256, member.sha256, `installed bytes differ from tar: ${key}`);
    }
    recordCheck('offline-local-tarball-install', { hooks: 'disabled', independent_working_directory: true });
    const help = await run('installed-help', command, ['--help']);
    assert(help.stdout.includes('NVCompact') || help.stdout.includes('nvcompact'));
    const version = await run('installed-version', command, ['--version']);
    assert(version.stdout.includes(scope.manifest.version));
    recordCheck('installed-bin-help-and-version');
    for (const name of ['build', 'resource', 'rewrite-c']) {
      const details = await run(`installed-${name}-help`, command, [name, '--help']);
      assert(details.stdout.includes('usage:'), `installed ${name} command did not load`);
    }
    recordCheck('installed-new-command-modules-load');

    const input = join(consumer, "number $(touch NVCOMPACT_SHELL_SENTINEL) ; 한글 ' .py");
    const output = join(consumer, "compressed [한글] ; ' .py");
    writeFileSync(input, '# ordinary comment\nanswer = (100000.0, 0.8, 0xFF)\nprint(answer)\n');
    await run('installed-notation', command, ['notation', input, '--language', 'python',
      '--token-contract', 'no-token-observation', '--compact', '--variant', 'shortest-compact',
      '--output', output, '--audit', join(consumer, 'notation.audit.json')]);
    assert(!existsSync(join(consumer, 'NVCOMPACT_SHELL_SENTINEL')), 'argument was interpreted by a shell');
    const pythonCommand = process.env.NVCOMPACT_PYTHON || 'python3';
    const interpreter = (await run('python-executable', pythonCommand, ['-c', 'import sys; print(sys.executable)'])).stdout.trim();
    assert(interpreter && existsSync(interpreter));
    const original = await run('notation-original-execution', interpreter, ['-B', input]);
    const compacted = await run('notation-compacted-execution', interpreter, ['-B', output]);
    assert.equal(compacted.stdout, original.stdout, 'notation changed independent interpreter output');
    assert(readFileSync(output).length < readFileSync(input).length, 'notation fixture was not compressed');
    recordCheck('notation-value-and-argv-preservation', { original_bytes: readFileSync(input).length,
      compacted_bytes: readFileSync(output).length, output: compacted.stdout.trim() });
    await run('missing-python', command, ['notation', input, '--language', 'python', '--list-variants'],
      { failure: true, env: { NVCOMPACT_PYTHON: join(temporary, 'python does not exist') } });
    await run('core-failure', command, ['notation', join(consumer, 'missing input.py'),
      '--language', 'python', '--list-variants'], { failure: true });
    recordCheck('missing-runtime-and-core-failure-remain-failures');

    assert.equal(process.platform, 'linux', 'native integration requires Linux');
    assert.equal(process.arch, 'x64', 'the bundled compact linker example targets x86-64');
    await run('cc-version', 'cc', ['--version']);
    await run('ld-version', 'ld', ['--version']);

    // Exercise the npm -> Python boundary, not just direct Python core calls.
    // The hook observes this Python process's own requests. Compiler children
    // and checker subprocesses with the core's clean environment are outside
    // that audit scope; the fixture's independent oracle checks actual I/O.
    const hook = join(consumer, 'native boundary audit');
    mkdirSync(hook);
    writeFileSync(join(hook, 'sitecustomize.py'), String.raw`import bz2, gzip, json, lzma, os, shutil, sys, zlib
_audit_path = os.environ["NVCOMPACT_PACKAGE_AUDIT"]
_only_cc = os.environ.get("NVCOMPACT_PACKAGE_ONLY_CC") == "1"
_cc = os.path.realpath(shutil.which("cc") or "")
def _record(event, **fields):
    with open(_audit_path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": event, **fields}) + "\n")
def _forbidden_compression(*args, **kwargs):
    _record("compression_attempt")
    raise RuntimeError("NVCOMPACT_NATIVE_COMPRESSION_FORBIDDEN")
for _module, _names in ((gzip, ("compress", "GzipFile")),
                        (zlib, ("compress", "compressobj")),
                        (bz2, ("compress", "BZ2Compressor", "BZ2File")),
                        (lzma, ("compress", "LZMACompressor", "LZMAFile"))):
    for _name in _names:
        setattr(_module, _name, _forbidden_compression)
def _audit(event, args):
    if event == "subprocess.Popen":
        executable, argv, cwd, environment = args
        command = [os.fsdecode(x) for x in argv] if isinstance(argv, (list, tuple)) else str(argv)
        _record(event, executable=os.fsdecode(executable), argv=command)
        if _only_cc and os.path.realpath(os.fsdecode(executable)) != _cc:
            _record("blocked_execution")
            raise RuntimeError("NVCOMPACT_NATIVE_EXECUTION_FORBIDDEN")
    elif event in ("os.system", "os.exec", "os.posix_spawn"):
        _record(event)
        if _only_cc:
            raise RuntimeError("NVCOMPACT_NATIVE_EXECUTION_FORBIDDEN")
sys.addaudithook(_audit)
_record("hook_loaded", argv=sys.argv)
`);
    function auditRecords(path) {
      assert(existsSync(path), 'the native audit hook did not run');
      return readFileSync(path, 'utf8').trim().split('\n').map(line => JSON.parse(line));
    }
    async function audited(name, argv, { onlyCompiler = false, failure = false, executable = command } = {}) {
      const auditPath = join(logs, `${name}.audit.jsonl`);
      const result = await run(name, executable, argv, { failure, timeout: 90000,
        env: { NVCOMPACT_PYTHON: interpreter, PYTHONPATH: hook,
          NVCOMPACT_PACKAGE_AUDIT: auditPath, NVCOMPACT_PACKAGE_ONLY_CC: onlyCompiler ? '1' : '0' } });
      const records = auditRecords(auditPath);
      assert(records.some(record => record.event === 'hook_loaded'), `${name}: audit not active`);
      if (!failure) {
        assert(!records.some(record => record.event === 'compression_attempt'), `${name}: used a compressor`);
        assert(!records.some(record => record.event === 'blocked_execution'), `${name}: attempted to run a noncompiler`);
      }
      return { result, records, audit: relative(repository, auditPath) };
    }
    const compressionProbe = await audited('native-compression-guard-positive-control',
      ['-B', '-c', 'import gzip; gzip.compress(b"probe")'], { executable: interpreter, failure: true });
    assert(compressionProbe.result.stderr.includes('NVCOMPACT_NATIVE_COMPRESSION_FORBIDDEN'));
    assert(compressionProbe.records.some(record => record.event === 'compression_attempt'));
    const executionProbe = await audited('native-execution-guard-positive-control',
      ['-B', '-c', 'import subprocess, sys; subprocess.run([sys.executable, "-c", "raise SystemExit(93)"], check=True)'],
      { executable: interpreter, failure: true, onlyCompiler: true });
    assert(executionProbe.result.stderr.includes('NVCOMPACT_NATIVE_EXECUTION_FORBIDDEN'));
    assert(executionProbe.records.some(record => record.event === 'blocked_execution'));
    recordCheck('native-boundary-audit-positive-controls', {
      compression_audit: compressionProbe.audit, execution_audit: executionProbe.audit });

    const plain = join(consumer, 'plain example from installed tarball');
    cpSync(join(installed, 'examples/native-build'), plain, { recursive: true });
    const plainManifest = join(plain, 'manifest.json');
    const plainBuild = join(consumer, 'plain linked build');
    const verifiedReplay = join(consumer, 'plain explicitly verified replay');
    const verifiedBuild = join(consumer, 'plain explicitly verified build');
    const plainReplay = join(consumer, 'plain replay of verified recipe');
    const plainRuns = [];
    plainRuns.push(await audited('installed-plain-build', ['build', plainManifest,
      '--out', plainBuild, '--jobs', '2', '--max-seconds', '45', '--command-seconds', '10'],
      { onlyCompiler: true }));
    const plainReport = json(join(plainBuild, 'report.json'));
    const plainRecipe = json(join(plainBuild, 'winner.recipe.json'));
    assert.equal(plainReport.status, 'built');
    assert.equal(plainReport.packing, 'none');
    assert.equal(plainReport.final_verification.status, 'not_run');
    assert.equal(plainReport.baseline.status, 'not_run');
    assert.equal(plainReport.screened_complete_files, 0);
    assert.equal(plainRecipe.verification, 'not_run');
    assert.deepEqual(Object.keys(plainRecipe.tools), ['cc']);
    const plainWinner = readFileSync(join(plainBuild, 'winner'));
    assert(plainWinner.equals(readFileSync(join(plainBuild, plainReport.winner.artifact))),
      'plain build changed the actual linked bytes');
    assert.equal(plainWinner.subarray(0, 5).toString('hex'), '7f454c4602');
    assert(plainWinner.readBigUInt64LE(40) > 0n, 'plain build removed the ELF section table');
    assert(plainWinner.readUInt16LE(60) > 0, 'plain build removed ELF section metadata');

    plainRuns.push(await audited('installed-plain-reproduce-verify', ['reproduce',
      join(plainBuild, 'winner.recipe.json'), '--out', verifiedReplay, '--verify',
      '--max-seconds', '45', '--command-seconds', '10', '--tool', `python=${interpreter}`]));
    const checkedReplay = json(join(verifiedReplay, 'reproduction.json'));
    assert.equal(checkedReplay.status, 'byte_identical');
    assert.equal(checkedReplay.verification.checker_output.status, 'passed');
    assert.equal(checkedReplay.verification.checker_output.integer_inputs, 256);
    assert.equal(checkedReplay.verification.checker_output.invalid_inputs, 2);
    assert(plainWinner.equals(readFileSync(join(verifiedReplay, 'winner'))));

    plainRuns.push(await audited('installed-plain-build-verify', ['build', plainManifest,
      '--out', verifiedBuild, '--verify', '--jobs', '2', '--max-seconds', '45',
      '--command-seconds', '10', '--tool', `python=${interpreter}`]));
    const checkedBuild = json(join(verifiedBuild, 'report.json'));
    assert.equal(checkedBuild.status, 'accepted');
    assert.equal(checkedBuild.packing, 'none');
    assert.equal(checkedBuild.final_verification.checker_output.status, 'passed');
    assert.equal(checkedBuild.final_verification.checker_output.integer_inputs, 256);
    assert.equal(checkedBuild.final_verification.checker_output.invalid_inputs, 2);
    assert(plainWinner.equals(readFileSync(join(verifiedBuild, 'winner'))));

    // A previously verified native recipe still needs this invocation's opt-in.
    plainRuns.push(await audited('installed-plain-reproduce', ['reproduce',
      join(verifiedBuild, 'winner.recipe.json'), '--out', plainReplay,
      '--max-seconds', '45', '--command-seconds', '10'], { onlyCompiler: true }));
    const uncheckedReplay = json(join(plainReplay, 'reproduction.json'));
    assert.equal(uncheckedReplay.status, 'byte_identical');
    assert.equal(uncheckedReplay.verification.status, 'not_run');
    assert(plainWinner.equals(readFileSync(join(plainReplay, 'winner'))));
    for (const [source, name] of [[join(plainBuild, 'report.json'), 'plain-build-report.json'],
      [join(plainBuild, 'winner.recipe.json'), 'plain-winner.recipe.json'],
      [join(verifiedReplay, 'reproduction.json'), 'plain-verified-reproduction.json'],
      [join(verifiedBuild, 'report.json'), 'plain-verified-build-report.json'],
      [join(plainReplay, 'reproduction.json'), 'plain-unverified-reproduction.json']]) {
      copyFileSync(source, join(logs, name));
    }
    recordCheck('installed-plain-build-and-explicit-execution', {
      scenario: 'The shipped native-build example, without source or manifest changes.',
      raw_linked_bytes: plainWinner.length, artifact_sha256: digest(plainWinner),
      default_build: 'built; baseline and artifact verification not run',
      default_reproduce: 'byte_identical; no execution despite a previously verified recipe',
      explicit_reproduce_oracle: checkedReplay.verification.checker_output,
      explicit_build_oracle: checkedBuild.final_verification.checker_output,
      compression_attempts: 0, audits: plainRuns.map(result => result.audit),
      audit_scope: 'Positive-controlled Python codec entry points and direct subprocess requests in the npm-launched core; no recursive compiler/checker instrumentation.' });

    const fixture = join(consumer, 'C-only example copied from installed tarball');
    mkdirSync(fixture);
    cpSync(join(installed, 'examples'), join(fixture, 'examples'), { recursive: true });
    cpSync(join(installed, 'linker'), join(fixture, 'linker'), { recursive: true });
    const originalManifest = join(fixture, 'examples/mixed/manifest-notation.json');
    const manifest = json(originalManifest);
    delete manifest.tools.rustc;
    for (const component of manifest.components) {
      component.variants = component.variants.filter(variant => variant.language !== 'rust');
      assert(component.variants.length > 0, 'C-only integration lost a required component');
    }
    manifest.inputs = manifest.inputs.filter(path => !path.endsWith('.rs'));
    const derivedManifest = join(fixture, 'examples/mixed/manifest-c-only.integration.json');
    writeFileSync(derivedManifest, JSON.stringify(manifest, null, 2) + '\n');
    copyFileSync(derivedManifest, join(logs, 'manifest-c-only.integration.json'));
    const build = join(consumer, 'native build'), replay = join(consumer, 'native replay');
    await run('installed-native-build', command, ['run', derivedManifest, '--out', build,
      '--jobs', '2', '--max-seconds', '90', '--command-seconds', '25', '--tool', `python=${interpreter}`],
      { timeout: 180000 });
    const buildReport = json(join(build, 'report.json'));
    assert.equal(buildReport.status, 'accepted');
    assert.equal(buildReport.search_complete, true);
    const finalOracle = json(buildReport.final_verification.stdout);
    assert.equal(finalOracle.ok, true);
    assert.equal(finalOracle.mode, 'full');
    assert(finalOracle.valid_records > 100000, 'full independent integer corpus was not executed');
    await run('installed-native-reproduce', command, ['reproduce', join(build, 'winner.recipe.json'),
      '--out', replay, '--max-seconds', '90', '--command-seconds', '25', '--tool', `python=${interpreter}`],
      { timeout: 180000 });
    const replayReport = json(join(replay, 'reproduction.json'));
    assert.equal(replayReport.status, 'byte_identical');
    const winner = readFileSync(join(build, 'winner'));
    assert(winner.equals(readFileSync(join(replay, 'winner'))));
    assert.equal(replayReport.sha256, digest(winner));
    const replayOracle = json(replayReport.verification.stdout);
    assert.equal(replayOracle.ok, true);
    assert.equal(replayOracle.mode, 'full');
    for (const [source, name] of [[join(build, 'report.json'), 'native-report.json'],
      [join(build, 'winner.recipe.json'), 'native-winner.recipe.json'],
      [join(replay, 'reproduction.json'), 'native-reproduction.json'],
      [buildReport.final_verification.stdout, 'native-final-oracle.json'],
      [replayReport.verification.stdout, 'native-replay-oracle.json']]) {
      copyFileSync(source, join(logs, name));
    }
    recordCheck('installed-c-only-build-and-fresh-reproduction', {
      scenario: 'Derived from shipped mixed notation manifest; only Rust variants/tool/inputs removed.',
      selected_link_candidates: buildReport.selected_link_candidates,
      screened_complete_files: buildReport.screened_complete_files,
      artifact_bytes: winner.length, artifact_sha256: digest(winner),
      final_oracle: finalOracle, replay_oracle: replayOracle,
      evidence: relative(repository, logs) });
    const after = inventory(installed);
    assert.deepEqual(after, before, 'running CLI changed the installed package');
    recordCheck('installed-package-unchanged', { files: Object.keys(after).length,
      scope: 'all regular file bytes and modes before/after commands; no added caches or outputs' });
    report.status = 'pass';
  } catch (error) {
    report.status = 'fail';
    report.error = { name: error.name, message: error.message };
  } finally {
    try {
      rmSync(temporary, { recursive: true });
      report.temporary_workspace_removed = true;
    } catch (error) {
      report.temporary_workspace_removed = false;
      report.cleanup_error = error.message;
      report.status = 'fail';
    }
    mkdirSync(join(repository, 'evidence'), { recursive: true });
    const serialized = JSON.stringify(report, null, 2) + '\n';
    writeFileSync(join(logs, 'report.json'), serialized);
    writeFileSync(join(repository, 'evidence/package-validation.json'), serialized);
  }
  return report;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const report = await verifyPackage(process.argv[2]);
  console.log(JSON.stringify({ status: report.status, package: report.package,
    checks: report.checks.map(check => check.name), report: 'evidence/package-validation.json',
    ...(report.error ? { error: report.error } : {}) }, null, 2));
  process.exitCode = report.status === 'pass' ? 0 : 1;
}
