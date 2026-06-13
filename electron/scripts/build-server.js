// Build the PyInstaller server binary and stage it for electron-builder.
//
// Runs `pyinstaller AR-TimeTracker.spec` in the project root, then copies the
// resulting one-file executable into electron/resources/server/, which
// electron-builder bundles as an extraResource. The packaged Electron app
// spawns this binary instead of `py -3 server.py`.

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const electronDir = path.join(__dirname, '..');
const projectRoot = path.join(electronDir, '..');
const isWin = process.platform === 'win32';
const exeName = isWin ? 'AR-TimeTracker.exe' : 'AR-TimeTracker';
const builtExe = path.join(projectRoot, 'dist', exeName);
const destDir = path.join(electronDir, 'resources', 'server');
const destExe = path.join(destDir, exeName);

function run(cmd, args, opts) {
  console.log(`\n> ${cmd} ${args.join(' ')}`);
  const r = spawnSync(cmd, args, { stdio: 'inherit', ...opts });
  if (r.error) throw r.error;
  if (r.status !== 0) throw new Error(`${cmd} exited with code ${r.status}`);
}

function resolvePyInstaller() {
  // PyInstaller doesn't yet support the very latest CPython, so prefer a pinned
  // 3.11 via the Windows `py` launcher, then fall back to PATH / other launchers.
  // Override with AR_PY env var (e.g. AR_PY="py -3.12").
  const probes = [];
  if (process.env.AR_PY) {
    const parts = process.env.AR_PY.split(' ');
    probes.push([parts[0], [...parts.slice(1), '-m', 'PyInstaller', '--version']]);
  }
  probes.push(
    ['py', ['-3.11', '-m', 'PyInstaller', '--version']],
    ['pyinstaller', ['--version']],
    ['py', ['-3', '-m', 'PyInstaller', '--version']],
    ['python', ['-m', 'PyInstaller', '--version']],
  );
  for (const probe of probes) {
    const r = spawnSync(probe[0], probe[1], { stdio: 'ignore' });
    if (!r.error && r.status === 0) return probe;
  }
  throw new Error('PyInstaller not found. Install it with: py -3 -m pip install pyinstaller');
}

console.log('Building server binary with PyInstaller...');
const [pyCmd, pyProbeArgs] = resolvePyInstaller();
const baseArgs = pyProbeArgs.slice(0, pyProbeArgs.length - 1); // drop trailing --version
run(pyCmd, [...baseArgs, '--noconfirm', '--clean', 'AR-TimeTracker.spec'], { cwd: projectRoot });

if (!fs.existsSync(builtExe)) {
  throw new Error(`Expected built binary not found at ${builtExe}`);
}

fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(builtExe, destExe);
console.log(`\nStaged server binary → ${destExe}`);
console.log('Done. electron-builder will bundle resources/server/.');
