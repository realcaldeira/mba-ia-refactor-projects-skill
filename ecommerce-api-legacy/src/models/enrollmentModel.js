'use strict';

const { Conflito } = require('../middlewares/errors');
const { PagamentoStatus } = require('./paymentModel');

class EnrollmentModel {
  constructor(db) {
    this.db = db;
  }

  async jaMatriculado(userId, courseId) {
    const linha = await this.db.get(
      'SELECT id FROM enrollments WHERE user_id = ? AND course_id = ?',
      [userId, courseId]
    );
    return Boolean(linha);
  }

  async criar(userId, courseId) {
    try {
      const { lastID } = await this.db.run(
        'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
        [userId, courseId]
      );
      return lastID;
    } catch (erro) {
      if (erro && (erro.code === 'SQLITE_CONSTRAINT' || String(erro.message).includes('UNIQUE'))) {
        throw new Conflito('Usuário já matriculado neste curso');
      }
      throw erro;
    }
  }

  async relatorioFinanceiro() {
    return this.db.all(
      `SELECT c.id           AS course_id,
              c.title        AS course_title,
              u.name         AS student_name,
              p.amount       AS payment_amount,
              p.status       AS payment_status
         FROM courses c
         LEFT JOIN enrollments e ON e.course_id = c.id
         LEFT JOIN users u       ON u.id = e.user_id
         LEFT JOIN payments p    ON p.enrollment_id = e.id
        ORDER BY c.id, e.id`
    );
  }
}

function montarRelatorio(linhas) {
  const porCurso = new Map();

  for (const linha of linhas) {
    if (!porCurso.has(linha.course_id)) {
      porCurso.set(linha.course_id, { course: linha.course_title, revenue: 0, students: [] });
    }
    if (linha.student_name === null && linha.payment_amount === null) continue;

    const curso = porCurso.get(linha.course_id);
    if (linha.payment_status === PagamentoStatus.PAGO) {
      curso.revenue += linha.payment_amount;
    }
    curso.students.push({
      student: linha.student_name ?? 'Unknown',
      paid: linha.payment_amount ?? 0,
    });
  }

  return [...porCurso.values()];
}

module.exports = { EnrollmentModel, montarRelatorio };
