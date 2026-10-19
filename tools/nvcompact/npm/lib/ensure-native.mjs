import { access, readFile, stat } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { packageRoot, platformKey } from './paths.mjs';

const binary = path.join(packageRoot, 'native', platformKey(), 'nvcompact');
try {
  if (!(await stat(binary)).isFile()) throw new Error('not a file');
  await access(binary, constants.X_OK);
  await readFile(path.join(packageRoot, 'native/runtime.json'));
} catch {
  throw new Error('This source directory has no staged Rust binary. Run npm run pack:nvcompact from Rove4k; it prepares the complete package outside the repository.');
}
