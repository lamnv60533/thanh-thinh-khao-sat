// Gộp phông Be Vietnam Pro (tiếng Việt + Latin) vào dev/src/index.html
// và ghi file triển khai ra index.html ở thư mục gốc của repo.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dev = dirname(fileURLToPath(import.meta.url));
const pkg = join(dev, 'node_modules/@fontsource/be-vietnam-pro');
const weights = [400, 600, 700];
const subsets = ['vietnamese', 'latin'];

let css = '';
for (const w of weights) {
  const sheet = readFileSync(join(pkg, `${w}.css`), 'utf8');
  for (const block of sheet.split('@font-face').slice(1)) {
    const file = (block.match(/url\(\.\/files\/([^)]+\.woff2)\)/) || [])[1];
    const range = (block.match(/unicode-range:\s*([^;]+);/) || [])[1];
    if (!file || !range) continue;
    if (!subsets.some((s) => file.includes(`-${s}-${w}-`))) continue;
    const b64 = readFileSync(join(pkg, 'files', file)).toString('base64');
    css += `@font-face{font-family:"Be Vietnam Pro";font-style:normal;font-display:swap;font-weight:${w};` +
      `src:url(data:font/woff2;base64,${b64}) format("woff2");unicode-range:${range.trim()}}\n`;
  }
}
const faces = (css.match(/@font-face/g) || []).length;
if (faces !== weights.length * subsets.length) throw new Error(`Số phông không đúng: ${faces}`);

const src = readFileSync(join(dev, 'src/index.html'), 'utf8');
if (!src.includes('/*__FONTS__*/')) throw new Error('Thiếu chỗ chèn phông trong src/index.html');
const out = join(dev, '..', 'index.html');
writeFileSync(out, src.replace('/*__FONTS__*/', css));
console.log('index.html', (readFileSync(out).length / 1024).toFixed(0) + ' KB');
