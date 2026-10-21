#!/usr/bin/env node
// Read-only comparison of complete envelope artifacts. Never starts an engine.
import { createHash } from 'node:crypto';
import { open, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_JSON = 32 * 1024 * 1024;
const MAX_ARTIFACT = 4 * 1024 * 1024;
const MAX_ENTRIES = 256;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const hashText = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

async function readBounded(filename, limit) {
  const handle = await open(filename, 'r');
  try {
    const stat = await handle.stat();
    requireValue(stat.isFile() && stat.size <= limit, `Not a bounded regular file: ${path.basename(filename)}`);
    // Read at most limit + 1 even if a writer grows the file after stat().
    const chunks = [];
    let count = 0;
    while (count <= limit) {
      const buffer = Buffer.alloc(Math.min(65536, limit + 1 - count));
      const { bytesRead } = await handle.read(buffer, 0, buffer.length, null);
      if (!bytesRead) break;
      chunks.push(buffer.subarray(0, bytesRead));
      count += bytesRead;
    }
    requireValue(count <= limit, `File grew beyond bound: ${path.basename(filename)}`);
    return Buffer.concat(chunks, count);
  } finally {
    await handle.close();
  }
}

async function json(filename) {
  return JSON.parse((await readBounded(filename, MAX_JSON)).toString('utf8'));
}

function validName(name) {
  return typeof name === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(name);
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

async function inspect(root, name, expected) {
  const directory = path.join(root, name);
  const summary = await json(path.join(directory, 'summary.json'));
  requireValue(summary.format === 'nvcompact.envelope.v2', 'Expected a completed Rust envelope v2 summary');
  requireValue(summary.name === name && summary.manifest?.name === name, 'Summary name differs from the expected row');
  requireValue(summary.manifest.category === expected.category, 'Submission category changed');
  requireValue(summary.original_sha256 === expected.sha256 && summary.manifest.sha256 === expected.sha256,
    'Original input hash differs from the independently pinned manifest');
  const winner = summary.winner;
  requireValue(winner && Number.isSafeInteger(winner.bytes) && winner.bytes >= 0 && hashText(winner.sha256),
    'Missing or malformed winner');
  const [original, smallest] = await Promise.all([
    readBounded(path.join(directory, 'original'), MAX_ARTIFACT),
    readBounded(path.join(directory, 'smallest'), MAX_ARTIFACT),
  ]);
  requireValue(digest(original) === expected.sha256, 'Actual original artifact hash differs from the manifest');
  requireValue(original.length === summary.original_bytes, 'Original byte count differs from the actual artifact');
  if (expected.original_bytes !== undefined) {
    requireValue(original.length === expected.original_bytes, 'Original byte count differs from the pinned manifest');
  }
  requireValue(digest(smallest) === winner.sha256 && smallest.length === winner.bytes,
    'Actual smallest artifact differs from its completed summary');
  requireValue(summary.no_size_regression === true && smallest.length <= original.length,
    'Candidate exceeds its original complete file');
  if (winner.id === 'identity') {
    requireValue(smallest.equals(original), 'Identity winner is not the original file');
  } else if (summary.manifest.envelope) {
    const payload = await readBounded(path.join(directory, 'selected-payload'), 16 * 1024 * 1024);
    const selectedHash = winner.payload_sha256 ?? summary.payload_sha256;
    requireValue(hashText(selectedHash) && digest(payload) === selectedHash,
      'Selected decoded payload differs from its recorded hash');
    requireValue(summary.smallest_payload_check?.tail_status === 'pass'
      && summary.smallest_payload_check?.decoder?.status === 'pass',
    'Selected deployment decoder check is missing or failed');
  }
  return { summary, original, smallest,
    value: { bytes: smallest.length, sha256: winner.sha256, variant: winner.variant,
      equivalence: winner.equivalence, protocol: summary.uci?.status ?? 'not_recorded',
      recorded_recipe_rebuild: summary.recipe_rebuild ?? null } };
}

/** Compare every row in a separately pinned manifest directory, with no execution. */
export async function compareResults({ baseline, candidate, manifests }) {
  requireValue(baseline && candidate && manifests, 'baseline, candidate and manifests directories are required');
  const directoryEntries = await readdir(manifests, { withFileTypes: true });
  requireValue(directoryEntries.length <= MAX_ENTRIES, 'Manifest directory exceeds the finite inventory bound');
  const names = directoryEntries.filter(entry => entry.isFile() && entry.name.endsWith('.json'))
    .map(entry => entry.name).sort();
  requireValue(names.length > 0, 'No comparison manifests found');
  const rows = [], seen = new Set();
  for (const filename of names) {
    let name = filename;
    try {
      const manifest = await json(path.join(manifests, filename));
      name = manifest.name;
      requireValue(validName(name) && !seen.has(name), 'Invalid or duplicate manifest name');
      seen.add(name);
      requireValue(['4k', '4k-elf'].includes(manifest.category) && hashText(manifest.sha256),
        'Manifest must pin a supported category and complete original SHA-256');
      const before = await inspect(baseline, name, manifest);
      const after = await inspect(candidate, name, manifest);
      requireValue(before.original.equals(after.original), 'Baseline and candidate have different original bytes');
      // An engine compiler or target change is not a source-portfolio regression comparison.
      for (const key of ['compile_argv', 'compile_limits', 'category', 'envelope']) {
        requireValue(JSON.stringify(canonical(before.summary.manifest[key] ?? null))
          === JSON.stringify(canonical(after.summary.manifest[key] ?? null)), `Comparison contract changed: ${key}`);
      }
      const noRegression = after.smallest.length <= before.smallest.length;
      rows.push({ name, category: manifest.category, original_sha256: manifest.sha256,
        original_bytes: before.original.length, baseline: before.value, candidate: after.value,
        saved_vs_baseline_bytes: before.smallest.length - after.smallest.length,
        status: noRegression ? 'pass' : 'size_regression', no_size_regression: noRegression });
    } catch (error) {
      let message = String(error.message ?? error);
      for (const [directory, label] of [[baseline, 'BASELINE'], [candidate, 'CANDIDATE'], [manifests, 'MANIFESTS']]) {
        message = message.split(path.resolve(directory)).join(label);
      }
      rows.push({ name, status: 'failed', no_size_regression: null, error: message });
    }
  }
  return { format: 'nvcompact.complete-file-regression.v1',
    status: rows.every(row => row.status === 'pass') ? 'pass' : 'fail',
    engine_or_verifier_started: false,
    scope: 'Actual complete artifact hashes and sizes against pinned inputs. Recorded decoder/recipe checks are inspected; no new semantic, protocol, runtime or strength proof is issued.',
    rows };
}

async function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    requireValue(['--baseline', '--candidate', '--manifests', '--output'].includes(key) && !(key.slice(2) in options),
      'Usage: compare-results.mjs --baseline DIR --candidate DIR --manifests DIR [--output NEW_JSON]');
    const value = argv[++i];
    requireValue(value && !value.startsWith('--'), `Missing value for ${key}`);
    options[key.slice(2)] = value;
  }
  const result = await compareResults(options);
  const data = JSON.stringify(result, null, 2) + '\n';
  if (options.output) await writeFile(options.output, data, { flag: 'wx' });
  process.stdout.write(data);
  process.exitCode = result.status === 'pass' ? 0 : 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 2; });
}
