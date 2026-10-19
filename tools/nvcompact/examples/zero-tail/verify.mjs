import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';

const binary = process.argv[2];
assert(binary, 'expected final artifact path');
async function run(input, expected, code = 0) {
  const child = spawn(binary, [], { timeout: 3000, killSignal: 'SIGKILL' });
  const stdout = [], stderr = [];
  let bytes = 0;
  const collect = destination => chunk => {
    bytes += chunk.length;
    if (bytes > 1 << 20) child.kill('SIGKILL');
    else destination.push(chunk);
  };
  child.stdout.on('data', collect(stdout));
  child.stderr.on('data', collect(stderr));
  const completion = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', (status, signal) => resolve({ status, signal }));
  });
  // Explicitly half-close stdin. An EOF-driven executable must not depend on a
  // synchronous spawn implementation deciding when to end its input stream.
  child.stdin.on('error', error => { if (error.code !== 'EPIPE') child.kill('SIGKILL'); });
  child.stdin.end(input);
  const result = await completion;
  assert.equal(result.signal, null);
  assert.equal(result.status, code);
  assert(bytes <= 1 << 20, 'output bound exceeded');
  assert.deepEqual(Buffer.concat(stdout), expected);
  assert.equal(Buffer.concat(stderr).length, 0);
}
const cells = new Uint8Array(8192);
cells[0] = 17;
const requests = [];
const responses = [];
function probe(index, value) {
  const request = Buffer.alloc(8);
  request.writeUInt32LE(index, 0);
  request.writeUInt32LE(value, 4);
  requests.push(request);
  const response = Buffer.alloc(4);
  response.writeUInt32LE(cells[index]);
  responses.push(response);
  cells[index] = value & 255;
}
// Observe every initialized zero, both sides of page boundaries, persistence,
// and the value conversion. This oracle does not inspect ELF header fields.
for (let i = 0; i < 8192; ++i) probe(i, (i * 37 + 19) >>> 0);
for (let i = 8191; i >= 0; --i) probe(i, 0xffffffff);
for (const i of [0, 1, 4095, 4096, 8191]) probe(i, 0);
await run(Buffer.concat(requests), Buffer.concat(responses));
await run(Buffer.alloc(0), Buffer.alloc(0));
for (let size = 1; size < 8; ++size) await run(Buffer.alloc(size), Buffer.alloc(0), 2);
for (const index of [8192, 0xffffffff]) {
  const input = Buffer.alloc(8);
  input.writeUInt32LE(index);
  await run(input, Buffer.alloc(0), 2);
}
process.stdout.write(JSON.stringify({ status: 'pass', records: requests.length, cases: 11 }) + '\n');
