'use strict';

const { gerarHash, conferirHash } = require('../middlewares/crypto');

/** A senha nunca aparece na serialização pública. */
const serializar = (linha) => ({ id: linha.id, name: linha.name, email: linha.email });

class UserModel {
  constructor(db) {
    this.db = db;
  }

  async buscarPorEmail(email) {
    return this.db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
  }

  async buscarCredencial(email) {
    return this.db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
  }

  async criar({ nome, email, senha }) {
    const { lastID } = await this.db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
      nome,
      email,
      gerarHash(senha),
    ]);
    return { id: lastID, name: nome, email };
  }

  /** Devolve o usuário quando a senha confere, ou null — sem dizer qual campo falhou. */
  async autenticar(email, senha) {
    const linha = await this.buscarCredencial(email);
    if (!linha || !conferirHash(senha, linha.pass)) return null;
    return serializar(linha);
  }

  /**
   * Remove o usuário e seus dependentes em uma transação.
   * Antes, a deleção deixava matrículas e pagamentos órfãos no banco.
   */
  async remover(id) {
    return this.db.transacao(async () => {
      const matriculas = await this.db.all('SELECT id FROM enrollments WHERE user_id = ?', [id]);
      for (const matricula of matriculas) {
        await this.db.run('DELETE FROM payments WHERE enrollment_id = ?', [matricula.id]);
      }
      await this.db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
      const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
      return { removido: changes > 0, matriculasRemovidas: matriculas.length };
    });
  }
}

module.exports = { UserModel, serializar };
