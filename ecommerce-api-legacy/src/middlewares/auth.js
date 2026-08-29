'use strict';

const crypto = require('crypto');
const { NaoAutorizado, Proibido } = require('./errors');

const b64 = (dados) => Buffer.from(dados).toString('base64url');

function gerarToken(usuario, segredo, ttlHoras = 8) {
  const payload = b64(
    JSON.stringify({
      sub: usuario.id,
      exp: Date.now() + ttlHoras * 3600 * 1000,
    })
  );
  const assinatura = crypto.createHmac('sha256', segredo).update(payload).digest('base64url');
  return `${payload}.${assinatura}`;
}

function validarToken(token, segredo) {
  const [payload, assinatura] = String(token).split('.');
  if (!payload || !assinatura) throw new NaoAutorizado('Token malformado');

  const esperada = crypto.createHmac('sha256', segredo).update(payload).digest('base64url');
  if (assinatura.length !== esperada.length) throw new NaoAutorizado('Token inválido');
  if (!crypto.timingSafeEqual(Buffer.from(assinatura), Buffer.from(esperada))) {
    throw new NaoAutorizado('Token inválido');
  }

  const dados = JSON.parse(Buffer.from(payload, 'base64url').toString());
  if (dados.exp < Date.now()) throw new NaoAutorizado('Token expirado');
  return dados;
}

function requerAutenticacao(segredo) {
  return (req, _res, next) => {
    const cabecalho = req.headers.authorization || '';
    if (!cabecalho.startsWith('Bearer ')) return next(new NaoAutorizado('Token ausente'));
    try {
      req.usuario = validarToken(cabecalho.slice(7), segredo);
      return next();
    } catch (erro) {
      return next(erro);
    }
  };
}

function requerPapel(papel) {
  return (req, _res, next) =>
    req.usuario?.papel === papel ? next() : next(new Proibido());
}

module.exports = { gerarToken, validarToken, requerAutenticacao, requerPapel };
