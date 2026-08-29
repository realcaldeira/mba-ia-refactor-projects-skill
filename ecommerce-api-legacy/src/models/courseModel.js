'use strict';

class CourseModel {
  constructor(db) {
    this.db = db;
  }

  async buscarAtivoPorId(id) {
    return this.db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]);
  }

  async listar() {
    return this.db.all('SELECT id, title, price, active FROM courses ORDER BY id');
  }
}

module.exports = { CourseModel };
