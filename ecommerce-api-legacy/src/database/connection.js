'use strict';

const sqlite3 = require('sqlite3');
const { promisify } = require('util');

function criarConexao(caminho = ':memory:') {
  const db = new sqlite3.Database(caminho);

  const run = (sql, params = []) =>
    new Promise((resolve, reject) => {
      db.run(sql, params, function callback(erro) {
        if (erro) return reject(erro);

        return resolve({ lastID: this.lastID, changes: this.changes });
      });
    });

  return {
    run,
    get: promisify(db.get.bind(db)),
    all: promisify(db.all.bind(db)),
    exec: promisify(db.exec.bind(db)),
    close: promisify(db.close.bind(db)),

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
