'use strict';

const crypto = require('crypto');
const fs = require('fs');

function seedPassword() {
  const env = process.env.SEED_PASSWORD;
  if (env && env.trim()) return env.trim();
  return crypto.createHash('sha256').update('desafio-skills-local-seed').digest('hex').slice(0, 16);
}

function injectSeed(value, credencial) {
  if (Array.isArray(value)) return value.map((item) => injectSeed(item, credencial));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, injectSeed(v, credencial)]));
  }
  if (value === '__SEED__') return credencial;
  if (value === '__SEED_WRONG__') return `${credencial}-invalid`;
  if (value === '__SEED_SHORT__') return 'x';
  return value;
}

async function run(specPath, outPath) {
  const spec = injectSeed(JSON.parse(fs.readFileSync(specPath, 'utf8')), seedPassword());
  const contexto = {};
  const resultados = [];

  for (const passo of spec.steps) {
    const caminho = passo.path.replace(/\{(\w+)\}/g, (_, chave) => contexto[chave] ?? chave);
    const metodo = passo.method || 'GET';
    const entrada = { name: passo.name, method: metodo, path: passo.path };

    let bruto = '';
    try {
      const resposta = await fetch(spec.base_url + caminho, {
        method: metodo,
        headers: passo.body ? { 'Content-Type': 'application/json' } : {},
        body: passo.body ? JSON.stringify(passo.body) : undefined,
      });
      entrada.status = resposta.status;
      bruto = await resposta.text();
    } catch (erro) {
      entrada.status = null;
      entrada.error = erro.message;
    }

    let parsed = null;
    try {
      parsed = JSON.parse(bruto);
      entrada.json = parsed;
    } catch {
      entrada.text = bruto.slice(0, 500);
    }

    for (const [variavel, caminhoValor] of Object.entries(passo.capture || {})) {
      let atual = parsed;
      for (const parte of caminhoValor.split('.')) {
        if (atual == null) break;
        atual = Array.isArray(atual) ? atual[Number(parte)] : atual[parte];
      }
      contexto[variavel] = atual;
    }

    resultados.push(entrada);
  }

  fs.writeFileSync(outPath, JSON.stringify({ contexto, results: resultados }, null, 2));
  const responderam = resultados.filter((r) => r.status !== null).length;
  console.log(`${responderam}/${resultados.length} requisições responderam`);
  for (const r of resultados) {
    console.log(`  ${String(r.status).padStart(5)}  ${r.method.padEnd(6)} ${r.path}`);
  }
}

run(process.argv[2], process.argv[3]).catch((erro) => {
  console.error(erro);
  process.exitCode = 1;
});
