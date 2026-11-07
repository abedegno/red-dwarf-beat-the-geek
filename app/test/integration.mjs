import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
const root = process.env.BTG_DATA_ROOT;
if (!root || !['public/catalog.json', 'analysis/extras/gateway.json'].every(p => existsSync(resolve(root, p)))) {
  console.error('Owner integration requires BTG_DATA_ROOT containing public/catalog.json and analysis/extras/gateway.json. See docs/setup.md.');
  process.exit(1);
}
const result = spawnSync(process.execPath, ['node_modules/vitest/vitest.mjs', 'run', '--mode', 'integration', ...process.argv.slice(2)], { stdio: 'inherit' });
process.exit(result.status ?? 1);
