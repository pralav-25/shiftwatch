import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const output = 'dist/client';
const homepage = join(output, 'index.html');
if (!existsSync(homepage))
  throw new Error('Static export is missing index.html; refusing to publish.');
const html = readFileSync(homepage, 'utf8');
const prefix =
  process.env.GITHUB_PAGES === 'true'
    ? 'https://pralav-25.github.io/shiftwatch'
    : '';
const assetUrls = [
  ...html.matchAll(/(?:src|href)="([^" ]*\/_next\/static\/[^" ]+)"/g),
].map((m) => m[1]);
if (assetUrls.length < 2)
  throw new Error('Missing expected stylesheet and script references.');
for (const url of assetUrls) {
  if (!url.startsWith(prefix + '/_next/static/'))
    throw new Error(`Unexpected asset prefix: ${url}`);
  const local = url.slice(prefix.length).split('?')[0];
  if (!existsSync(join(output, local)))
    throw new Error(`Export references a missing asset: ${local}`);
}
console.log(
  `Static export verified: index.html and ${assetUrls.length} asset references.`,
);
