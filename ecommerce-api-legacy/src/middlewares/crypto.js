'use strict';

const crypto = require('crypto');

const TAMANHO_SALT = 16;
const TAMANHO_CHAVE = 64;

function gerarHash(senha) {
  const salt = crypto.randomBytes(TAMANHO_SALT).toString('hex');
  const derivada = crypto.scryptSync(senha, salt, TAMANHO_CHAVE).toString('hex');
  return `scrypt$${salt}$${derivada}`;
}

function conferirHash(senha, armazenado) {
  if (typeof armazenado !== 'string' || !armazenado.startsWith('scrypt$')) return false;
  const [, salt, esperado] = armazenado.split('$');
  const derivada = crypto.scryptSync(senha, salt, TAMANHO_CHAVE).toString('hex');

  return crypto.timingSafeEqual(Buffer.from(derivada, 'hex'), Buffer.from(esperado, 'hex'));
}

module.exports = { gerarHash, conferirHash };
