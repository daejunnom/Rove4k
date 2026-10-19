import assert from 'node:assert/strict';
import { lstat, mkdtemp, mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { artifactRoot, execute, externalDirectory, hash, json, platformKey, writeJson } from './common.mjs';

const artifacts = await externalDirectory(artifactRoot());
const packaged = await json(path.join(artifacts, 'package.json'));
assert.equal(packaged.status, 'packed');
assert.equal(hash(await readFile(packaged.path)), packaged.sha256, 'package changed after packing');
const parent = path.join(artifacts, 'installed-verification'); await mkdir(parent, { recursive: true });
const work = await mkdtemp(path.join(parent, 'consumer 한글 with spaces-'));
const logs = path.join(work, 'logs');
const env = { ...process.env, npm_config_cache: path.join(work, 'npm-cache') };
delete env.NVCOMPACT_BIN; delete env.NVCOMPACT_ARTIFACT_DIR;
await writeJson(path.join(work, 'package.json'), { name: 'nvcompact-offline-consumer', version: '1.0.0', private: true });
const records = [];
const invoke = async (command, args, options = {}) => {
  const result = await execute(command, args, { cwd: work, env, logs, ...options, allowFailure: true });
  records.push({ command, args, code: result.code, seconds: result.seconds,
    stdout_sha256: hash(result.stdout), stderr_sha256: hash(result.stderr),
    stdout_path: path.relative(work, result.stdout_path), stderr_path: path.relative(work, result.stderr_path) });
  assert(result.code === 0 && !result.interrupted, `${command} failed (${result.code ?? result.signal}): ${result.stderr.toString('utf8').slice(-8192)}; logs: ${logs}`);
  return result;
};
try {
await invoke(process.env.NVCOMPACT_NPM ?? 'npm', ['install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', packaged.path]);
const installed = path.join(work, 'node_modules/@rove4k/nvcompact');
assert(!(await lstat(installed)).isSymbolicLink(), 'installation must contain a package, not a workspace link');
async function inventory(directory, base = directory) {
  const result = {};
  for (const entry of (await readdir(directory, { withFileTypes: true })).sort((a,b) => a.name.localeCompare(b.name))) {
    const file = path.join(directory, entry.name);
    assert(!entry.isSymbolicLink(), 'package content must not link outside itself');
    if (entry.isDirectory()) Object.assign(result, await inventory(file, base));
    else { const data = await readFile(file); result[path.relative(base, file)] = { bytes: data.length, sha256: hash(data), mode: (await stat(file)).mode & 0o777 }; }
  }
  return result;
}
const before = await inventory(installed);
assert(before[`native/${platformKey()}/nvcompact`]);
assert.equal(before[`native/${platformKey()}/nvcompact`].sha256, packaged.runtime.sha256);
assert.equal(before[`native/${platformKey()}/nvcompact`].bytes, packaged.runtime.bytes);
assert.equal(before[`native/${platformKey()}/nvcompact`].mode, 0o755);
assert(Object.keys(before).every(name => !/(?:^|\/)(?:vendor|inputs|reference)(?:\/|$)|\.py$|\.rs$|\.c$/.test(name)));
const bin = path.join(work, 'node_modules/.bin/nvcompact');
const run = async (args, options) => await invoke(bin, args, options);
const version = await run(['--version']);
assert.equal(version.stdout.toString('utf8').trim(), `nvcompact ${packaged.version}`);
const help = await run(['--help']);
assert.match(help.stdout.toString('utf8'), /envelope/);
const doctor = JSON.parse((await run(['doctor', '--json'])).stdout);
assert.equal(doctor.runtime, 'Rust'); assert.equal(doctor.python_backend, false); assert.equal(doctor.targets_started, false);

const project = path.join(work, 'owned native fixture'); await mkdir(project);
const source = '#include <stdio.h>\nint main(void){unsigned x;int n;while((n=scanf("%u",&x))==1){if(x>255)return 64;printf("%u\\n",x*x);}return n==EOF?0:64;}\n';
await writeFile(path.join(project, 'main.c'), source);
const oracle = String.raw`import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {closeSync,openSync} from 'node:fs';
import {appendFile,mkdtemp,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
async function run(input){
  const work=await mkdtemp(path.join(process.cwd(),'oracle-'));
  const names=['stdin','stdout','stderr'].map(name=>path.join(work,name));
  await writeFile(names[0],input);
  const fds=[openSync(names[0],'r'),openSync(names[1],'wx'),openSync(names[2],'wx')];
  let code;
  try{
    code=await new Promise((resolve,reject)=>{
      const child=spawn(process.argv[2],[],{stdio:fds});
      let timedOut=false;
      const timer=setTimeout(()=>{timedOut=true;child.kill('SIGKILL');},3000);
      child.once('error',error=>{clearTimeout(timer);reject(error);});
      child.once('close',value=>{clearTimeout(timer);if(timedOut)reject(new Error('target timeout'));else resolve(value);});
    });
  }finally{for(const fd of fds)closeSync(fd);}
  return {code,out:await readFile(names[1],'utf8'),err:await readFile(names[2],'utf8')};
}
const values=Array.from({length:256},(_,i)=>i);
assert.deepEqual(await run(values.join('\n')+'\n'),{code:0,out:values.map(i=>i*i).join('\n')+'\n',err:''});
for(const bad of ['256\n','x\n'])assert.deepEqual(await run(bad),{code:64,out:'',err:''});
await appendFile(process.env.NVCOMPACT_ORACLE_LOG,'passed\n');
console.log(JSON.stringify({status:'passed',normal_inputs:256,invalid_inputs:2}));
`;
await writeFile(path.join(project, 'verify.mjs'), oracle);
const oracleEvents = path.join(work, 'oracle-events.txt');
const manifest = { project_root: '.', target: packaged.runtime.rust_host, inputs: ['main.c','verify.mjs'],
  environment: { NVCOMPACT_ORACLE_LOG: oracleEvents },
  tools: { cc: { executable: 'cc' }, node: { executable: process.execPath } },
  components: [{ id: 'program', contract: 'Read uint32 values 0..255; print exact squares; invalid token/value exits 64; no other effects',
    variants: [{ id: 'raw', language: 'c', sources: ['main.c'], commands: [['{cc}','-std=c11','-Os','-ffile-prefix-map={root}=.','-c','{source}','-o','{object}']] }] }],
  build_profiles: [{ id: 'size' }],
  link_profiles: [{ id: 'hosted', argv: ['{cc}','{objects}','-Wl,--build-id=none','-o','{binary}'] }],
  verify: ['{node}','{root}/verify.mjs','{binary}'], verify_final: ['{node}','{root}/verify.mjs','{binary}'],
  baseline: { build: 'size', link: 'hosted', order: ['program'], variants: { program: 'raw' } }, codecs: ['xz-6'] };
const manifestPath = path.join(project, 'manifest.json'); await writeJson(manifestPath, manifest);
const plain = path.join(work, 'plain');
const built = JSON.parse((await run(['build', manifestPath, '--out', plain, '--jobs', '1'])).stdout);
assert.equal(built.status, 'built'); assert.equal(built.packing, 'none'); assert.equal(built.final_verification.status, 'not_run');
assert.equal((await readFile(path.join(plain, 'winner'))).subarray(0,4).toString('hex'), '7f454c46');
await assert.rejects(readFile(oracleEvents), { code: 'ENOENT' });
const replay = JSON.parse((await run(['reproduce', path.join(plain, 'winner.recipe.json'), '--out', path.join(work, 'plain-replay')])).stdout);
assert.equal(replay.status, 'byte_identical'); assert.equal(replay.verification.status, 'not_run');
const verifiedPath = path.join(work, 'verified');
const verified = JSON.parse((await run(['build', manifestPath, '--out', verifiedPath, '--verify', '--jobs', '1'])).stdout);
assert.equal(verified.status, 'accepted');
const verificationEvents = await readFile(oracleEvents, 'utf8');
assert.match(verificationEvents, /^passed\n/);
const defaultReplay = JSON.parse((await run(['reproduce', path.join(verifiedPath, 'winner.recipe.json'), '--out', path.join(work, 'verified-replay-default')])).stdout);
assert.equal(defaultReplay.verification.status, 'not_run');
assert.equal(await readFile(oracleEvents, 'utf8'), verificationEvents);
const requestedReplay = JSON.parse((await run(['reproduce', path.join(verifiedPath, 'winner.recipe.json'), '--out', path.join(work, 'verified-replay-explicit'), '--verify'])).stdout);
assert.equal(requestedReplay.verification.status, 'pass');
assert((await readFile(oracleEvents, 'utf8')).length > verificationEvents.length);
const spelling = 'unsigned long long x=0x0000000000000001ULL;\n';
await writeFile(path.join(work, 'spelling 한글.c'), spelling);
await run(['notation', path.join(work, 'spelling 한글.c'), '--language', 'c', '--target', 'c11-lp64', '--token-contract', 'no-token-observation', '--compact', '--output', path.join(work, 'short.c')]);
assert((await readFile(path.join(work, 'short.c'))).length < Buffer.byteLength(spelling));
assert.deepEqual(await inventory(installed), before, 'installed package changed while executing');
const report = { format: 'nvcompact.npm-install-validation.v1', status: 'pass',
  package_sha256: packaged.sha256, runtime_sha256: packaged.runtime.sha256,
  node: process.version, platform_key: platformKey(), installed_package: installed,
  checks: ['offline actual tarball installation','native --version and command discovery','Rust doctor without targets',
    'raw ELF build with no verifier execution','independent exact native replay',
    'explicit verification of 256 integer cases and 2 invalid cases',
    'verified recipe still requires --verify for new execution','typed source notation',
    'installed package bytes and modes unchanged; no external engine sources'],
  commands: records, fixture_input_count: 256, fixture_invalid_count: 2,
  engine_tests: 'none; owned tiny fixture only', registry_publication: false };
await writeJson(path.join(work, 'report.json'), report);
await writeJson(path.join(artifacts, 'package-validation.json'), report);
process.stdout.write(`${JSON.stringify({ status: report.status, checks: report.checks.length, commands: records.length,
  package_sha256: report.package_sha256, report: path.join(work, 'report.json') }, null, 2)}\n`);
} catch (error) {
  const report = { format: 'nvcompact.npm-install-validation.v1', status: 'failed',
    package_sha256: packaged.sha256, runtime_sha256: packaged.runtime.sha256,
    node: process.version, platform_key: platformKey(), work, error: String(error.stack ?? error), commands: records,
    engine_tests: 'none; owned tiny fixture only', registry_publication: false };
  await writeJson(path.join(work, 'report.json'), report);
  await writeJson(path.join(artifacts, 'package-validation.json'), report);
  throw error;
}
