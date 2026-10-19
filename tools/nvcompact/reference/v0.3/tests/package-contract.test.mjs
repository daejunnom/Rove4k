import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
import { captureProcess, inspectTarball, validatePackageScope } from '../scripts/verify-package.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

test('actual npm tarball contains the standalone CLI and complete linked examples', { timeout: 60000 }, async () => {
  const temporary = mkdtempSync(join(tmpdir(), 'nvcompact npm tar scope '));
  try {
    const config = join(temporary, 'empty.npmrc');
    writeFileSync(config, '');
    const packed = await captureProcess('npm', ['pack', '--workspace', 'packages/nvcompact', '--json',
      '--offline', '--ignore-scripts', '--pack-destination', temporary], {
      cwd: root, encoding: 'utf8', shell: false, timeout: 45000, maxBuffer: 4 * 1024 * 1024,
      env: { ...process.env, npm_config_userconfig: config,
        npm_config_cache: join(temporary, 'npm-cache'), npm_config_offline: 'true' }
    });
    assert.equal(packed.error, undefined, packed.error?.message);
    assert.equal(packed.status, 0, packed.stderr);
    const metadata = JSON.parse(packed.stdout);
    assert.equal(metadata.length, 1);
    const archive = inspectTarball(join(temporary, metadata[0].filename));
    const scope = validatePackageScope(archive);
    assert.equal(scope.manifest.version, metadata[0].version);
    assert.equal(archive.bytes, metadata[0].size);
    const byPath = new Map(archive.members.map(member => [member.name.slice('package/'.length), member]));
    for (const name of ['examples/mixed/manifest.json', 'examples/mixed/manifest-notation.json']) {
      const manifest = JSON.parse(byPath.get(name).data.toString('utf8'));
      for (const input of manifest.inputs) {
        const resolved = posix.normalize(posix.join(posix.dirname(name), manifest.project_root ?? '.', input));
        assert(!resolved.startsWith('../') && !posix.isAbsolute(resolved), `example leaves package: ${input}`);
        assert(byPath.has(resolved), `shipped example references absent input: ${resolved}`);
      }
    }
    // A tarball may be installed with scripts disabled: all runtime files must
    // already be present, and core migration must preserve source bytes.
    for (const member of archive.members.filter(member => member.name.startsWith('package/python/')
      && member.type === '0')) {
      const original = join(root, 'packages/nvcompact', member.name.slice('package/'.length));
      assert(existsSync(original));
      assert(member.data.equals(readFileSync(original)), `tar changed Python source: ${member.name}`);
    }
  } finally {
    rmSync(temporary, { recursive: true });
  }
});
