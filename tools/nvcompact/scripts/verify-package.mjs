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
  const { expectedCode = 0, ...executionOptions } = options;
  const result = await execute(command, args, { cwd: work, env, logs, ...executionOptions, allowFailure: true });
  records.push({ command, args, code: result.code, expected_code: expectedCode,
    signal: result.signal, interrupted: result.interrupted, seconds: result.seconds,
    stdout_sha256: hash(result.stdout), stderr_sha256: hash(result.stderr),
    stdout_path: path.relative(work, result.stdout_path), stderr_path: path.relative(work, result.stderr_path) });
  assert(result.code === expectedCode && !result.interrupted, `${command} returned ${result.code ?? result.signal}; expected ${expectedCode}: ${result.stderr.toString('utf8').slice(-8192)}; logs: ${logs}`);
  return result;
};
try {
await invoke(process.env.NVCOMPACT_NPM ?? 'npm', ['install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', packaged.path]);
const installed = path.join(work, 'node_modules', packaged.name);
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
assert.match(help.stdout.toString('utf8'), /cleanup-source/);
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
const cppAdviceSource = 'bool rank(int to){if(to<0||to>127)return false;return (to>>4)==0||(to>>4)==7;}\n'
  + 'unsigned long long repeated(unsigned long long x,int unused){int spare=0;return (x&0x5555555555555555ULL)|0x5555555555555555ULL;}\n'
  + 'static int dormant(){return 1;}\n';
const rustAdviceSource = 'pub fn rank(to:i32)->bool{if to<0||to>127{return false;}(to>>4)==0||(to>>4)==7}\n'
  + 'fn repeated(x:u64,unused:i32)->u64{let spare:i32=0;(x&0x5555555555555555u64)|0x5555555555555555u64}\n';
const cppAdvicePath = path.join(work, 'advice.cpp');
const rustAdvicePath = path.join(work, 'advice.rs');
await writeFile(cppAdvicePath, cppAdviceSource);
await writeFile(rustAdvicePath, rustAdviceSource);
const absentSource = path.join(work, 'absent-advice-input');
const absentCompiler = path.join(work, 'absent-advice-compiler');
const cleanupPath = path.join(work, 'cleanup.cpp');
const cleanup = JSON.parse((await run(['cleanup-source', cppAdvicePath, '--language', 'cpp',
  '--token-contract', 'no-token-observation', '--clang', process.env.NVCOMPACT_CLANG ?? 'clang',
  '--output', cleanupPath, '--variant', 'cleanup-functions'])).stdout);
assert(cleanup.variants.some(variant => variant.id === 'cleanup-functions'));
assert(!(await readFile(cleanupPath, 'utf8')).includes('dormant'));
assert.equal(await readFile(cppAdvicePath, 'utf8'), cppAdviceSource);
for (const language of ['rust', 'python']) {
  const unexpected = path.join(work, `unexpected-${language}-cleanup`);
  const rejected = await run(['cleanup-source', absentSource, '--language', language,
    '--clang', absentCompiler, '--portfolio', unexpected], { expectedCode: 2 });
  assert.match(rejected.stderr.toString('utf8'), /unsupported/);
  assert.equal(rejected.stdout.length, 0);
  await assert.rejects(lstat(unexpected), { code: 'ENOENT' });
}
const cppAdvice = JSON.parse((await run(['advise-source', cppAdvicePath, '--language', 'cpp',
  '--clang', process.env.NVCOMPACT_CLANG ?? 'clang'])).stdout);
const rustAdvice = JSON.parse((await run(['advise-source', rustAdvicePath, '--language', 'rust',
  '--clang', absentCompiler])).stdout);
function checkStaticAdvice(report, input, language) {
  assert.equal(report.frontend.language, language);
  assert.equal(report.source_sha256, hash(Buffer.from(input)));
  assert.equal(report.advisory_only, true);
  assert.equal(report.complete, true);
  assert.equal(report.statistics.source_modified, false);
  assert.equal(report.statistics.compression_candidates_created, 0);
  assert.equal(report.statistics.final_file_bytes_measured, false);
  assert.deepEqual(report.expressions, [], 'a private C carrier is not source-language evidence');
  assert(report.ranges.some(site => site.symbol === 'to' && site.minimum === '0' && site.maximum === '127'));
  assert(report.ranges.every(site => !site.instrumentable));
}
checkStaticAdvice(cppAdvice, cppAdviceSource, 'c++');
checkStaticAdvice(rustAdvice, rustAdviceSource, 'rust');
for (const [report, kind, input, literal] of [
  [cppAdvice, 'duplicate-constant', cppAdviceSource, '0x5555555555555555ULL'],
  [rustAdvice, 'repeated_constant', rustAdviceSource, '0x5555555555555555u64'],
]) {
  const repeated = report.findings.find(finding => finding.kind === kind && finding.original === literal);
  assert(repeated, `missing typed repeated constant for ${report.frontend.language}`);
  assert.equal(repeated.related_locations.length, 1);
  for (const location of [repeated.location, ...repeated.related_locations]) {
    assert.equal(input.slice(location.start, location.end), literal);
  }
}
for (const symbol of ['unused', 'spare', 'dormant']) {
  assert(cppAdvice.findings.some(finding => finding.kind === 'no-reference' && finding.symbol === symbol));
}
for (const symbol of ['unused', 'spare']) {
  assert(rustAdvice.findings.some(finding => finding.kind === 'unused_binding' && finding.symbol === symbol));
}
const rankOriginal = '(to>>4)==0||(to>>4)==7';
const cppRank = cppAdvice.language_details.expressions.find(site => site.original === rankOriginal);
assert(cppRank);
assert.equal(cppRank.result_type, 'bool');
assert.equal(cppRank.value_category, 'prvalue');
assert(cppRank.comparison.candidates.some(candidate => candidate.source === '!(to+16&96)'
  && candidate.evidence.checked_values === 128 && candidate.evidence.cpp_surface_type_and_category_preserved));
assert(cppAdvice.findings.some(finding => finding.original === rankOriginal
  && finding.assurance === 'exhaustive-static-cpp-containing-domain'));
const rustRank = rustAdvice.language_details.expressions.find(site => site.original === rankOriginal);
assert(rustRank);
assert.equal(rustRank.result_type, 'bool');
assert.deepEqual(rustRank.domain_values, Array.from({ length: 128 }, (_, value) => String(value)));
assert(rustRank.candidates.some(candidate => candidate.source === 'to+16&96==0'
  && candidate.evidence.checked_values === 128 && candidate.evidence.same_result_type
  && candidate.evidence.domain_sha256 === rustRank.domain_sha256));
assert(rustAdvice.findings.some(finding => finding.original === rankOriginal
  && finding.assurance === 'exhaustive_rust_typed_static_domain'));

const repeatedBytes = Buffer.concat([Buffer.from('abc'), Buffer.alloc(8, 0x55), Buffer.from('12345'), Buffer.alloc(8, 0x55)]);
const artifactPath = path.join(work, 'owned repeated bytes');
await writeFile(artifactPath, repeatedBytes);
const binaryAdvice = JSON.parse((await run(['inspect-binary', artifactPath, '--word-bytes', '8'])).stdout);
assert.equal(binaryAdvice.advisory_only, true);
assert.equal(binaryAdvice.input_sha256, hash(repeatedBytes));
assert.equal(binaryAdvice.scan.complete, true);
const magic = binaryAdvice.findings.find(finding => finding.bytes_hex === '5555555555555555');
assert(magic);
assert.deepEqual(magic.offsets, [3, 16]);
assert.equal(magic.occurrences, 2);
assert.equal(magic.semantic_constant, null);
assert.equal(magic.estimated_savings_bytes, null);

const pythonReport = path.join(work, 'unexpected-python-report.json');
const unsupported = await run(['advise-source', absentSource, '--language', 'python', '--clang', absentCompiler,
  '--report', pythonReport], { expectedCode: 2 });
assert.match(unsupported.stderr.toString('utf8'), /unsupported advisory language/);
assert.equal(unsupported.stdout.length, 0);
await assert.rejects(lstat(pythonReport), { code: 'ENOENT' });
for (const language of ['cpp', 'rust']) {
  for (const option of ['--profile', '--instrument']) {
    const requestedPath = path.join(work, `unexpected-${language}-${option.slice(2)}`);
    const reportPath = `${requestedPath}.json`;
    const rejected = await run(['advise-source', absentSource, '--language', language, '--clang', absentCompiler,
      option, requestedPath, '--report', reportPath], { expectedCode: 2 });
    assert.match(rejected.stderr.toString('utf8'), /static-only/);
    assert.equal(rejected.stdout.length, 0);
    await assert.rejects(lstat(requestedPath), { code: 'ENOENT' });
    await assert.rejects(lstat(reportPath), { code: 'ENOENT' });
  }
}
await assert.rejects(lstat(absentSource), { code: 'ENOENT' });
await assert.rejects(lstat(absentCompiler), { code: 'ENOENT' });
assert.equal(await readFile(cppAdvicePath, 'utf8'), cppAdviceSource);
assert.equal(await readFile(rustAdvicePath, 'utf8'), rustAdviceSource);
assert.deepEqual(await readFile(artifactPath), repeatedBytes);
assert.deepEqual(await inventory(installed), before, 'installed package changed while executing');
const report = { format: 'nvcompact.npm-install-validation.v1', status: 'pass',
  package_sha256: packaged.sha256, runtime_sha256: packaged.runtime.sha256,
  node: process.version, platform_key: platformKey(), installed_package: installed,
  checks: ['offline actual tarball installation','native --version and command discovery','Rust doctor without targets',
    'raw ELF build with no verifier execution','independent exact native replay',
    'explicit verification of 256 integer cases and 2 invalid cases',
    'verified recipe still requires --verify for new execution','typed source notation',
    'installed C++ cleanup candidate and explicit Rust/Python cleanup rejection before input/output access',
    'installed C++ typed constants, unused declarations, read domains and type/category-preserving n-version advice',
    'installed Rust typed constants, unused bindings, read domains and typed n-version advice without a compiler',
    'installed final-artifact byte inventory without semantic-constant or savings claims',
    'unsupported Python rejected before source/compiler access or report creation',
    'C++/Rust dynamic profile and instrumentation rejected before source/output access',
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
