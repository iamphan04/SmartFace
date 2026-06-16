import { cp, mkdir, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { build } from 'esbuild-wasm';

const frontendDir = path.resolve(fileURLToPath(new URL('..', import.meta.url)));
const distDir = path.join(frontendDir, 'dist-app');
const assetsDir = path.join(distDir, 'assets');
const publicDir = path.join(frontendDir, 'public');

await rm(distDir, { recursive: true, force: true });
await mkdir(assetsDir, { recursive: true });
await cp(publicDir, distDir, { recursive: true });

await build({
  absWorkingDir: frontendDir,
  entryPoints: ['src/main.jsx'],
  outdir: assetsDir,
  entryNames: 'app',
  assetNames: '[name]-[hash]',
  bundle: true,
  define: {
    'process.env.NODE_ENV': '"production"',
  },
  format: 'esm',
  jsx: 'automatic',
  legalComments: 'none',
  loader: {
    '.jpg': 'file',
    '.jpeg': 'file',
    '.png': 'file',
    '.svg': 'file',
  },
  minify: true,
  platform: 'browser',
  target: ['es2020'],
});

await writeFile(
  path.join(distDir, 'index.html'),
  `<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="/assets/app.css" />
    <title>SmartFace</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/app.js"></script>
  </body>
</html>
`,
  'utf8',
);

console.log(`Frontend da build tai ${distDir}`);
