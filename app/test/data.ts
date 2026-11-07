import { resolve } from 'node:path';
/** BTG_DATA_ROOT contains public/ and analysis/ from an owner preparation. */
export function dataPath(path: string): string {
  const root = process.env.BTG_DATA_ROOT;
  if (!root) return resolve(path);
  return resolve(root, path.replace(/^\.\.\//, ''));
}
