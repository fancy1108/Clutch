import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const script = path.join(repoRoot, 'scripts', 'tauri-dev.py');
const python = process.platform === 'win32' ? 'python' : 'python3';

const child = spawn(python, [script], { stdio: 'inherit', cwd: repoRoot, shell: false });
child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});
