import assert from 'node:assert/strict';
import { access, readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const readJson = async (p) => JSON.parse(await readFile(path.join(root, p), 'utf8'));
const workspace = await readJson('package.json');
const pkg = await readJson('packages/nvcompact/package.json');
const lab = await readJson('packages/tcec4k-lab/package.json');

assert.equal(workspace.private, true, 'the workspace root is not a distributable package');
assert.equal(lab.private, true, 'the third-party experiment collection stays a private workspace');
assert.equal(lab.dependencies[pkg.name], pkg.version, 'use the local CLI workspace version');
assert.ok(pkg.bin.nvcompact, 'the CLI must expose its documented executable');
await access(path.join(root, 'packages/nvcompact', pkg.bin.nvcompact));
for (const name of ['nvcompact.py', 'nvpack.py', 'nvelf.py', 'nvnotation.py', 'nvenvelope.py', 'nvuci.py', 'nvreproduce.py', 'run_engines.py', 'nvlaunch.py', 'nvresource.py', 'nvcflow.py']) {
  await access(path.join(root, 'packages/nvcompact/python', name));
}
const unexpected = ['preinstall', 'install', 'postinstall', 'prepare'].filter((x) => pkg.scripts?.[x]);
assert.deepEqual(unexpected, [], 'this package has no installation-time builds or downloads');

const manifests = (await readdir(path.join(root, 'packages/tcec4k-lab/engines'))).filter((n) => n.endsWith('.json'));
assert.ok(manifests.length > 0, 'the lab must contain actual inputs');
for (const name of manifests) {
  const file = path.join(root, 'packages/tcec4k-lab/engines', name);
  const m = JSON.parse(await readFile(file, 'utf8'));
  for (const relative of [m.artifact, m.provenance?.source_archive, ...(m.provenance?.license_paths ?? [])].filter(Boolean)) {
    await access(path.resolve(path.dirname(file), relative));
  }
}
console.log(JSON.stringify({ status: 'pass', package: pkg.name, version: pkg.version, fixture_manifests: manifests.length }));
