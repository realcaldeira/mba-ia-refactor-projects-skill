'use strict';

/** Logger com níveis — substitui os console.log espalhados (e o PAN que vazava no log). */
const NIVEIS = { error: 0, warn: 1, info: 2, debug: 3 };

function criarLogger(nivel = 'info') {
  const limite = NIVEIS[nivel] ?? NIVEIS.info;
  const emitir = (n) => (mensagem, contexto) => {
    if (NIVEIS[n] > limite) return;
    const linha = `${new Date().toISOString()} ${n.toUpperCase().padEnd(5)} ${mensagem}`;
    console[n === 'debug' ? 'log' : n](contexto ? `${linha} ${JSON.stringify(contexto)}` : linha);
  };
  return { error: emitir('error'), warn: emitir('warn'), info: emitir('info'), debug: emitir('debug') };
}

module.exports = { criarLogger };
