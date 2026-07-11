import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const orchestrator = path.join(repoRoot, 'services', 'orchestrator');
const script = path.join(repoRoot, 'scripts', 'build-sidecar.py');
const python = process.platform === 'win32' ? 'python' : 'python3';
const venvPython = process.platform === 'win32'
  ? path.join(orchestrator, '.venv', 'Scripts', 'python.exe')
  : path.join(orchestrator, '.venv', 'bin', 'python');

function canRun(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, stdio: 'ignore', shell: false });
  return !result.error && result.status === 0;
}

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, stdio: 'inherit', shell: false });
  if (result.error) {
    console.error(`[build-sidecar] failed to start ${command}: ${result.error.message}`);
    process.exit(1);
  }
  process.exit(result.status ?? 1);
}

const envUv = process.env.CLUTCH_UV_BIN || process.env.UV_EXE || process.env.UV;
if (envUv && canRun(envUv, ['--version'])) {
  run(envUv, ['run', '--project', orchestrator, 'python', script]);
}

if (canRun('uv', ['--version'])) {
  run('uv', ['run', '--project', orchestrator, 'python', script]);
}

if (canRun(python, ['-m', 'uv', '--version'])) {
  run(python, ['-m', 'uv', 'run', '--project', orchestrator, 'python', script]);
}

if (existsSync(venvPython)) {
  run(venvPython, [script]);
}

console.error('[build-sidecar] uv was not found and services/orchestrator/.venv is missing.');
console.error('[build-sidecar] Run `python -m uv sync --extra dev` in services/orchestrator, then retry.');
process.exit(1);
