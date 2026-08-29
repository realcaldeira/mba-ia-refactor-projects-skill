'use strict';

/** Status de pagamento como constante de domínio, no lugar das strings soltas. */
const PagamentoStatus = Object.freeze({ PAGO: 'PAID', RECUSADO: 'DENIED' });

class PaymentModel {
  constructor(db) {
    this.db = db;
  }

  async registrar(enrollmentId, valor, status) {
    const { lastID } = await this.db.run(
      'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
      [enrollmentId, valor, status]
    );
    return lastID;
  }

  async receitaPorCurso(courseId) {
    const linha = await this.db.get(
      `SELECT COALESCE(SUM(p.amount), 0) AS receita
         FROM payments p
         JOIN enrollments e ON e.id = p.enrollment_id
        WHERE e.course_id = ? AND p.status = ?`,
      [courseId, PagamentoStatus.PAGO]
    );
    return linha.receita;
  }
}

module.exports = { PaymentModel, PagamentoStatus };
