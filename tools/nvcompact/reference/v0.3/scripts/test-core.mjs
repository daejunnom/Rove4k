import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const executable = process.env.NVCOMPACT_PYTHON || 'python3';
const child = spawn(executable, ['-B', '-m', 'unittest', 'discover', '-s', 'packages/nvcompact/python/tests', '-v'], {
  cwd: root, stdio: 'inherit', shell: false,
});
child.once('error', (error) => { console.error(error.message); process.exitCode = 1; });
child.once('exit', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : signal === 'SIGTERM' ? 143 : 1); });
