import { chmod, mkdir, mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { artifactRoot, copyOwnFile, execute, externalDirectory, hash, json, packageRoot, packedPackage, platformKey, repositoryRoot, sourceFingerprint, writeJson } from './common.mjs';

const args = process.argv.slice(2);
if (args.some(arg => arg !== '--no-build')) throw new Error('Supported option: --no-build (requires a matching prepared Rust build).');
const artifacts = await externalDirectory(artifactRoot());
if (!args.includes('--no-build')) {
  const build = await execute(process.execPath, [fileURLToPath(new URL('./build.mjs', import.meta.url))]);
  process.stdout.write(build.stdout); process.stderr.write(build.stderr);
}
const prepared = await json(path.join(artifacts, 'build.json'));
const current = await sourceFingerprint();
const bytes = await readFile(prepared.binary);
if (prepared.platform_key !== platformKey() || prepared.source.sha256 !== current.sha256 || hash(bytes) !== prepared.sha256) {
  throw new Error('The prepared native build does not match current inputs, host, or bytes. Rebuild before packaging.');
}
const stagingRoot = path.join(artifacts, 'staging'); await mkdir(stagingRoot, { recursive: true });
const stage = await mkdtemp(path.join(stagingRoot, 'package-'));
for (const directory of ['bin', 'lib']) {
  for (const entry of await readdir(path.join(packageRoot, directory), { withFileTypes: true })) {
    if (!entry.isFile()) throw new Error(`Unexpected package entry ${directory}/${entry.name}`);
    await copyOwnFile(path.join(packageRoot, directory, entry.name), path.join(stage, directory, entry.name), directory === 'bin');
  }
}
for (const name of ['README.md', 'package.json']) await copyOwnFile(path.join(packageRoot, name), path.join(stage, name));
await copyOwnFile(path.join(repositoryRoot, 'LICENSE'), path.join(stage, 'LICENSE'));
const nativeDirectory = path.join(stage, 'native', platformKey()); await mkdir(nativeDirectory, { recursive: true });
await writeFile(path.join(nativeDirectory, 'nvcompact'), bytes);
const packageMetadata = await json(path.join(stage, 'package.json'));
if (packageMetadata.version !== prepared.version) {
  throw new Error('The npm package version must match the prepared Rust runtime. Rebuild after synchronizing package versions.');
}
if (!packageMetadata.os.includes(process.platform) || !packageMetadata.cpu.includes(process.arch)
    || (packageMetadata.libc?.includes('glibc') && !process.report.getReport().header.glibcVersionRuntime)) {
  throw new Error('The npm package targets Linux x64 with glibc; this host requires a separately declared target package.');
}
await writeJson(path.join(stage, 'package.json'), packageMetadata);
const runtime = { format: 'nvcompact.npm-native.v1', version: prepared.version, platform_key: prepared.platform_key,
  rust_host: prepared.rust_host, rustc: prepared.rustc, source_sha256: current.sha256,
  cargo_lock_sha256: current.files['Cargo.lock'], bytes: prepared.bytes, sha256: prepared.sha256 };
await writeJson(path.join(stage, 'native/runtime.json'), runtime);
await chmod(path.join(nativeDirectory, 'nvcompact'), 0o755);
const dist = path.join(artifacts, 'packages'); await mkdir(dist, { recursive: true });
const result = await execute(process.env.NVCOMPACT_NPM ?? 'npm', ['pack', '--offline', '--ignore-scripts', '--json', '--pack-destination', dist],
  { cwd: stage, env: { ...process.env, npm_config_cache: path.join(artifacts, 'npm-cache') } });
const info = packedPackage(result.stdout.toString('utf8'), packageMetadata);
const files = info.files.map(file => file.path);
if (!files.includes(`native/${platformKey()}/nvcompact`) || files.some(file => /(?:^|\/)(?:vendor|inputs|reference)(?:\/|$)|\.py$|\.rs$|\.c$/.test(file))) {
  throw new Error('Package file inventory violates the native-tool-only packaging contract.');
}
const tarball = path.join(dist, info.filename);
const report = { format: 'nvcompact.npm-pack.v1', status: 'packed', name: info.name, version: info.version,
  private: packageMetadata.private === true, published: false, platform_key: platformKey(), path: tarball, bytes: (await readFile(tarball)).length,
  sha256: hash(await readFile(tarball)), runtime, files: info.files };
await writeJson(path.join(artifacts, 'package.json'), report);
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
