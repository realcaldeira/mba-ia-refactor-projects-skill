'use strict';

/** Compara duas execuções do smoke e falha se algum status divergir. */
const fs = require('fs');

const indexar = (caminho) =>
  Object.fromEntries(JSON.parse(fs.readFileSync(caminho, 'utf8')).results.map((r) => [r.name, r]));

const antes = indexar(process.argv[2]);
const depois = indexar(process.argv[3]);
const falhas = [];

for (const [nome, a] of Object.entries(antes)) {
  const d = depois[nome];
  if (!d) falhas.push(`${nome}: ausente depois`);
  else if (a.status !== d.status) falhas.push(`${nome}: ${a.status} -> ${d.status}`);
}

console.log(`${Object.keys(antes).length} endpoints comparados`);
console.log(falhas.length ? `DIVERGENCIAS:\n  ${falhas.join('\n  ')}` : 'PARIDADE OK');
process.exitCode = falhas.length ? 1 : 0;
