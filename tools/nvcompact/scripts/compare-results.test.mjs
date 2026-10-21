import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { compareResults } from './compare-results.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');

test('complete-file comparison measures bytes and rejects missing, altered and changed-input rows', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'nvcompact-regression-'));
  try {
    const original = Buffer.from('owned fixture only');
    const expected = { name: 'sample', category: '4k-elf', sha256: hash(original), original_bytes: original.length };
    const manifests = path.join(root, 'manifests');
    await mkdir(manifests);
    await writeFile(path.join(manifests, 'sample.json'), JSON.stringify(expected));
    const baseline = path.join(root, 'baseline'), candidate = path.join(root, 'candidate');
    const summary = { format: 'nvcompact.envelope.v2', name: 'sample', manifest: expected,
      original_sha256: expected.sha256, original_bytes: original.length, no_size_regression: true,
      recipe_rebuild: 'pass; a separate reproduce invocation is still recorded independently',
      winner: { id: 'identity', bytes: original.length, sha256: expected.sha256, variant: 'raw',
        equivalence: 'complete submitted file byte identity' }, uci: { status: 'not_run' } };
    for (const directory of [baseline, candidate]) {
      await mkdir(path.join(directory, 'sample'), { recursive: true });
      await writeFile(path.join(directory, 'sample', 'original'), original);
      await writeFile(path.join(directory, 'sample', 'smallest'), original);
      await writeFile(path.join(directory, 'sample', 'summary.json'), JSON.stringify(summary));
    }
    const compare = () => compareResults({ baseline, candidate, manifests });
    assert.equal((await compare()).status, 'pass');
    await writeFile(path.join(candidate, 'sample', 'smallest'), Buffer.alloc(original.length, 0));
    assert.match((await compare()).rows[0].error, /Actual smallest artifact differs/);
    await writeFile(path.join(candidate, 'sample', 'smallest'), original);
    const changed = structuredClone(summary); changed.original_sha256 = '0'.repeat(64);
    await writeFile(path.join(candidate, 'sample', 'summary.json'), JSON.stringify(changed));
    assert.match((await compare()).rows[0].error, /Original input hash differs/);
    await writeFile(path.join(candidate, 'sample', 'summary.json'), JSON.stringify(summary));
    // Both outputs remain <= original, but the new output regresses against the old selected minimum.
    const shorter = original.subarray(0, original.length - 1);
    const selected = structuredClone(summary);
    selected.winner = { ...selected.winner, id: 'native-candidate', bytes: shorter.length, sha256: hash(shorter) };
    await writeFile(path.join(baseline, 'sample', 'smallest'), shorter);
    await writeFile(path.join(baseline, 'sample', 'summary.json'), JSON.stringify(selected));
    const regression = await compare();
    assert.equal(regression.status, 'fail');
    assert.equal(regression.rows[0].status, 'size_regression');
    assert.equal(regression.rows[0].saved_vs_baseline_bytes, -1);
    await writeFile(path.join(manifests, 'missing.json'), JSON.stringify({ ...expected, name: 'missing' }));
    const missing = await compare();
    assert.equal(missing.status, 'fail');
    assert.equal(missing.rows.find(row => row.name === 'missing').status, 'failed');
    assert.equal(missing.engine_or_verifier_started, false);
  } finally {
    await rm(root, { recursive: true });
  }
});
