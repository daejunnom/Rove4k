import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const packageRoot = fileURLToPath(new URL('../', import.meta.url));
export const repositoryRoot = path.resolve(packageRoot, '../../..');

export function artifactRoot(env = process.env, root = repositoryRoot) {
  if (env.NVCOMPACT_ARTIFACT_DIR) return path.resolve(env.NVCOMPACT_ARTIFACT_DIR);
  const key = createHash('sha256').update(root).digest('hex').slice(0, 16);
  return path.join(os.tmpdir(), 'rove4k-nvcompact', key);
}

export function platformKey() {
  return `${process.platform}-${process.arch}`;
}
