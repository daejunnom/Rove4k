import { spawn } from 'node:child_process';
import { constants } from 'node:os';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const packageRoot = new URL('../', import.meta.url);
const metadata = JSON.parse(readFileSync(new URL('package.json', packageRoot), 'utf8'));
const launcher = fileURLToPath(new URL('python/nvlaunch.py', packageRoot));
const commands = new Set(['build', 'run', 'reproduce', 'notation', 'rewrite-c', 'envelope', 'uci', 'replay', 'engines', 'resource']);

export function helpText() {
  return `NVCompact ${metadata.version} — build, rewrite and compaction portfolio tools

Usage: nvcompact <command> [arguments]

  build        Compile and link without packing; execution checks need --verify
  run          Build and compare verified implementation/link/packing portfolios
  reproduce    Rebuild a selected native-link recipe
  notation     Generate value/type-preserving source spelling candidates
  rewrite-c    Generate typed C rewrite candidates and an optional run manifest
  envelope     Compare complete self-extracting file candidates
  uci          Validate an actual artifact with the TCEC 4K UCI subset
  replay       Independently replay a selected envelope recipe
  engines      Run local manifests (explicit --manifests DIR is required)
  resource     Plan resource-heavy UCI tests; run requires explicit --start
  doctor       Check the local Python/stdlib runtime; add --json for JSON

  nvcompact <command> --help   Show that command's Python CLI options
  nvcompact --version         Show this npm package's version

Requires Linux, Node.js >=22 and CPython >=3.11. Compilers, engine runtimes,
and the optional chess oracle are separate prerequisites. No installation or
download is performed. NVCOMPACT_PYTHON selects one Python executable path;
spaces are accepted literally, and command strings are never shell-evaluated.
Input/output paths are relative to your current working directory.
`;
}

export function resolvePython(env = process.env) {
  const value = env.NVCOMPACT_PYTHON;
  if (value === undefined) return 'python3';
  if (typeof value !== 'string' || value.length === 0 || value.includes('\0')) {
    throw new Error('NVCOMPACT_PYTHON must be one nonempty executable path, not shell arguments');
  }
  return value;
}

export function commandFor(argv, env = process.env) {
  const [command, ...args] = argv;
  if (!commands.has(command) && command !== 'doctor') {
    throw new Error(`unknown command ${JSON.stringify(command)}; run nvcompact --help`);
  }
  if (args.some(value => typeof value !== 'string' || value.includes('\0'))) {
    throw new Error('arguments must be strings without NUL bytes');
  }
  return { executable: resolvePython(env), args: ['-B', launcher, command, ...args] };
}

function launch(plan, { env, cwd, stderr }) {
  return new Promise(resolve => {
    // The Python adapter owns cleanup. It lives in a separate session so a
    // terminal Ctrl-C reaches Node once; relay to its PID, never blind-kill a
    // group before nested helpers have unwound their own cleanup.
    let child;
    let pendingSignal;
    let sentSignal = false;
    let settled = false;
    const relay = signal => {
      if (pendingSignal) return;
      pendingSignal = signal;
      if (child?.pid) { sentSignal = true; child.kill(signal); }
    };
    const interrupt = () => relay('SIGINT');
    const terminate = () => relay('SIGTERM');
    const finish = code => {
      if (settled) return;
      settled = true;
      process.removeListener('SIGINT', interrupt);
      process.removeListener('SIGTERM', terminate);
      resolve(code);
    };
    process.on('SIGINT', interrupt);
    process.on('SIGTERM', terminate);
    try {
      child = spawn(plan.executable, plan.args, {
        cwd, env, stdio: 'inherit', shell: false, detached: true,
      });
    } catch (error) {
      stderr.write(`nvcompact: could not launch Python: ${error.message}\n`);
      finish(2);
      return;
    }
    child.once('spawn', () => {
      if (pendingSignal && !sentSignal) { sentSignal = true; child.kill(pendingSignal); }
    });
    child.once('error', error => {
      stderr.write(`nvcompact: could not launch ${JSON.stringify(plan.executable)}: ${error.message}\n`);
      stderr.write('Set NVCOMPACT_PYTHON to one installed CPython >=3.11 executable path.\n');
      finish(error.code === 'ENOENT' ? 127 : error.code === 'EACCES' ? 126 : 2);
    });
    child.once('close', (code, signal) => {
      finish(code ?? (signal ? 128 + (constants.signals[signal] ?? 0) : 2));
    });
  });
}

export async function main(argv = process.argv.slice(2), {
  env = process.env, cwd = process.cwd(), stdout = process.stdout, stderr = process.stderr,
} = {}) {
  if (Number(process.versions.node.split('.')[0]) < 22) {
    stderr.write('nvcompact: Node.js >=22 is required.\n');
    return 2;
  }
  if (argv.length === 0 || ['--help', '-h', 'help'].includes(argv[0])) {
    if (argv[0] === 'help' && argv.length === 2 && commands.has(argv[1])) {
      argv = [argv[1], '--help'];
    } else {
      stdout.write(helpText());
      return 0;
    }
  }
  if (argv.length === 1 && ['--version', '-v', 'version'].includes(argv[0])) {
    stdout.write(`${metadata.version}\n`);
    return 0;
  }
  if (process.platform !== 'linux') {
    stderr.write('nvcompact: this release supports Linux only; use a Linux environment with its required tools.\n');
    return 2;
  }
  try {
    return await launch(commandFor(argv, env), { env, cwd, stderr });
  } catch (error) {
    stderr.write(`nvcompact: ${error.message}\n`);
    return 2;
  }
}
