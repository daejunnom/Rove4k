import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { buildEnvironment, execute, hash, json, packageRoot, platformKey, repositoryRoot, sourceFingerprint, writeJson } from './common.mjs';

if (process.platform !== 'linux') throw new Error('The current NVCompact runtime supports Linux.');
const state = await buildEnvironment();
const metadata = await json(path.join(packageRoot, 'package.json'));
const before = await sourceFingerprint();
const rustc = await execute(process.env.RUSTC ?? 'rustc', ['--version', '--verbose'], { env: state.env });
const host = /^host: (.+)$/m.exec(rustc.stdout.toString('utf8'))?.[1];
if (!host || !host.includes('linux')) throw new Error('Unable to determine the Linux Rust host target.');
const result = await execute(process.env.NVCOMPACT_CARGO ?? 'cargo', ['build', '--locked', '--release', '--target', host,
  '--manifest-path', path.join(repositoryRoot, 'Cargo.toml'), '-p', 'nvcompact', '--bin', 'nvcompact'], { env: state.env });
process.stdout.write(result.stdout); process.stderr.write(result.stderr);
const after = await sourceFingerprint();
if (after.sha256 !== before.sha256) throw new Error('Rust inputs changed during compilation. Finish the source edit and rebuild; no stale package was prepared.');
const binary = path.join(state.target, host, 'release', 'nvcompact');
const bytes = await readFile(binary);
if (!bytes.subarray(0, 4).equals(Buffer.from([127, 69, 76, 70]))) throw new Error('The prepared tool is not a native ELF executable.');
const version = await execute(binary, ['--version'], { env: state.env });
if (version.stdout.toString('utf8').trim() !== `nvcompact ${metadata.version}`) throw new Error('Rust and npm versions disagree.');
const record = { format: 'nvcompact.npm-build.v1', version: metadata.version, binary, platform_key: platformKey(),
  rust_host: host, rustc: rustc.stdout.toString('utf8').trim(), source: after, bytes: bytes.length, sha256: hash(bytes) };
await writeJson(path.join(state.artifacts, 'build.json'), record);
process.stdout.write(`${JSON.stringify({ status: 'built', binary, bytes: record.bytes, sha256: record.sha256, metadata: path.join(state.artifacts, 'build.json') }, null, 2)}\n`);
