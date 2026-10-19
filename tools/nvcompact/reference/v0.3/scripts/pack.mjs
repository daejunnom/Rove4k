import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, openSync, writeSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
async function execute(command, args, capture = false) {
  const owned = await mkdtemp(path.join(tmpdir(), 'nvcompact-pack-'));
  const output = path.join(owned, 'stdout');
  const config = path.join(owned, 'npmrc');
  await writeFile(config, '');
  const fd = capture ? openSync(output, 'w') : null;
  try {
    const result = await new Promise((resolve, reject) => {
      const child = spawn(command, args, { cwd: root, shell: false,
        env: { ...process.env, npm_config_cache: path.join(owned, 'cache'), npm_config_userconfig: config },
        stdio: capture ? ['ignore', fd, 'inherit'] : 'inherit' });
      child.once('error', reject);
      child.once('close', (code, signal) => resolve({ code, signal }));
    });
    const stdout = capture ? await readFile(output, 'utf8') : '';
    if (Buffer.byteLength(stdout) > 4 * 1024 * 1024) throw new Error('npm pack output exceeds the metadata limit');
    return { ...result, stdout };
  } finally {
    if (fd !== null) closeSync(fd);
    await rm(owned, { recursive: true, force: true });
  }
}
const checked = await execute(process.execPath, [path.join(root, 'scripts/check.mjs')]);
if (checked.code !== 0) process.exit(checked.code ?? 1);
const destination = path.join(root, 'dist');
await mkdir(destination, { recursive: true });
const packed = await execute('npm', ['pack', '--workspace=nvcompact', '--pack-destination', destination, '--ignore-scripts', '--json'], true);
if (packed.code !== 0) {
  if (packed.stdout) process.stdout.write(packed.stdout);
  process.exit(packed.code ?? 1);
}
const records = JSON.parse(packed.stdout);
if (records.length !== 1) throw new Error('expected one CLI tarball');
const record = records[0];
const file = path.join(destination, record.filename);
record.sha256 = createHash('sha256').update(await readFile(file)).digest('hex');
await writeFile(path.join(destination, 'pack.json'), JSON.stringify(records, null, 2) + '\n');
writeSync(1, JSON.stringify({ file: path.relative(root, file), bytes: record.size, unpacked_bytes: record.unpackedSize, sha256: record.sha256, entries: record.entryCount }) + '\n');
