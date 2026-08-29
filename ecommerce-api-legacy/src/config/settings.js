'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function carregarEnv(arquivo = path.resolve(process.cwd(), '.env')) {
  let texto;
  try {
    texto = fs.readFileSync(arquivo, 'utf8');
  } catch (erro) {
    if (erro.code === 'ENOENT') return;
    throw erro;
  }
  for (const linha of texto.split('\n')) {
    const trimmed = linha.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    const chave = trimmed.slice(0, eq).trim();
    let valor = trimmed.slice(eq + 1).trim();
    if (
      (valor.startsWith('"') && valor.endsWith('"')) ||
      (valor.startsWith("'") && valor.endsWith("'"))
    ) {
      valor = valor.slice(1, -1);
    }
    if (process.env[chave] === undefined) process.env[chave] = valor;
  }
}

carregarEnv();

const toBool = (valor, padrao = false) =>
  valor === undefined || valor === '' ? padrao : ['1', 'true', 'yes', 'on'].includes(String(valor).toLowerCase());

const envOu = (nome, padrao) => {
  const valor = process.env[nome];
  if (valor === undefined || String(valor).trim() === '') return padrao;
  return valor;
};

const settings = {
  port: Number(envOu('PORT', 3000)),
  host: envOu('HOST', '127.0.0.1'),
  dbPath: envOu('DB_PATH', ':memory:'),
  ambiente: envOu('NODE_ENV', 'desenvolvimento'),
  logLevel: envOu('LOG_LEVEL', 'info'),
  seedOnBoot: toBool(process.env.SEED_ON_BOOT, true),
  auth: {
    secret: envOu('SECRET_KEY', crypto.createHash('sha256').update('desafio-skills-dev-key').digest('hex')),
    tokenTtlHoras: Number(envOu('TOKEN_TTL_HORAS', 8)),
    required: toBool(process.env.AUTH_REQUIRED, false),
  },
  payment: {
    gatewayKey: envOu('PAYMENT_GATEWAY_KEY', ''),
    gatewayUrl: envOu('PAYMENT_GATEWAY_URL', ''),
  },
  smtp: {
    user: envOu('SMTP_USER', ''),
    pass: envOu('SMTP_PASS', ''),
  },
};

function validar(config = settings) {
  if (!config.auth.secret || !String(config.auth.secret).trim()) {
    throw new Error('SECRET_KEY não pode ser vazia');
  }
  const devKey = crypto.createHash('sha256').update('desafio-skills-dev-key').digest('hex');
  if (config.ambiente !== 'production' && config.ambiente !== 'producao') return config;
  if (config.auth.secret === devKey) {
    throw new Error('SECRET_KEY precisa ser definida fora de desenvolvimento');
  }
  if (!config.payment.gatewayKey) {
    throw new Error('PAYMENT_GATEWAY_KEY precisa ser definida fora de desenvolvimento');
  }
  return config;
}

module.exports = { settings, validar, carregarEnv };
