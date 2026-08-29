'use strict';

class AuditLogModel {
  constructor(db) {
    this.db = db;
  }

  async registrar(acao) {
    await this.db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [
      acao,
    ]);
  }
}

module.exports = { AuditLogModel };
