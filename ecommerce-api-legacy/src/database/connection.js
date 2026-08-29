'use strict';

const sqlite3 = require('sqlite3');
const { promisify } = require('util');

/**
 * Cria a conexão e devolve a API já promisificada.
 * A conversão de callbacks acontece aqui, uma única vez — o resto da aplicação usa async/await.
 */
function criarConexao(caminho = ':memory:') {
  const db = new sqlite3.Database(caminho);

  const run = (sql, params = []) =>
    new Promise((resolve, reject) => {
      db.run(sql, params, function callback(erro) {
        if (erro) return reject(erro);
        // `this` do sqlite3 carrega lastID/changes — por isso não é arrow function.
        return resolve({ lastID: this.lastID, changes: this.changes });
      });
    });

  return {
    run,
    get: promisify(db.get.bind(db)),
    all: promisify(db.all.bind(db)),
    exec: promisify(db.exec.bind(db)),
    close: promisify(db.close.bind(db)),
    /** Unidade de trabalho: ou todas as escritas acontecem, ou nenhuma. */
    async transacao(operacao) {
      await run('BEGIN');
      try {
        const resultado = await operacao();
        await run('COMMIT');
        return resultado;
      } catch (erro) {
        await run('ROLLBACK');
        throw erro;
      }
    },
  };
}

module.exports = { criarConexao };
