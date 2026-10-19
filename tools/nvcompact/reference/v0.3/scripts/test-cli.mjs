// Import the node:test suites in one process. This uses the public test API
// on both Node 22 and 24 without depending on a version-specific CLI flag.
import { readdir } from 'node:fs/promises';

const directory = new URL('../tests/', import.meta.url);
const files = (await readdir(directory)).filter(name => name.endsWith('.test.mjs')).sort();
if (!files.length) throw new Error('No CLI test suites were found');
for (const file of files) await import(new URL(file, directory));
