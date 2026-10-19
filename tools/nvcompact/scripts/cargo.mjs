import { buildEnvironment, execute, repositoryRoot } from './common.mjs';

const state = await buildEnvironment();
const result = await execute(process.env.NVCOMPACT_CARGO ?? 'cargo', process.argv.slice(2), { cwd: repositoryRoot, env: state.env });
process.stdout.write(result.stdout); process.stderr.write(result.stderr);
