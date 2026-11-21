import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Compile the tested module and its relative imports in memory. No generated
// files or additional test-only bundler dependency are needed.
const modules = new Map();
async function moduleUrl(url) {
  if (modules.has(url.href)) return modules.get(url.href);
  const result = (async () => {
    const source = await readFile(url, 'utf8');
    let { outputText } = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
    });
    const imports = [...outputText.matchAll(/from\s+['"](\.[^'"]+)['"]/g)];
    for (const match of imports) {
      const path = match[1].endsWith('.ts') ? match[1] : `${match[1]}.ts`;
      const dependency = await moduleUrl(new URL(path, url));
      outputText = outputText.replace(match[0], `from '${dependency}'`);
    }
    return `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`;
  })();
  modules.set(url.href, result);
  return result;
}

export async function load(name) {
  return import(await moduleUrl(new URL(`../../src/${name}.ts`, import.meta.url)));
}
