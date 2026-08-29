'use strict';

const { PagamentoStatus } = require('../models/paymentModel');
const { gerarHash } = require('../middlewares/crypto');

const DDL = [
  `CREATE TABLE IF NOT EXISTS users (
     id INTEGER PRIMARY KEY,
     name TEXT NOT NULL,
     email TEXT NOT NULL UNIQUE,
     pass TEXT NOT NULL
   )`,
  `CREATE TABLE IF NOT EXISTS courses (
     id INTEGER PRIMARY KEY,
     title TEXT NOT NULL,
     price REAL NOT NULL,
     active INTEGER NOT NULL DEFAULT 1
   )`,
  `CREATE TABLE IF NOT EXISTS enrollments (
     id INTEGER PRIMARY KEY,
     user_id INTEGER NOT NULL REFERENCES users(id),
     course_id INTEGER NOT NULL REFERENCES courses(id)
   )`,
  `CREATE TABLE IF NOT EXISTS payments (
     id INTEGER PRIMARY KEY,
     enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
     amount REAL NOT NULL,
     status TEXT NOT NULL
   )`,
  `CREATE TABLE IF NOT EXISTS audit_logs (
     id INTEGER PRIMARY KEY,
     action TEXT NOT NULL,
     created_at DATETIME NOT NULL
   )`,
  'CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id)',
  'CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id)',
  'CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments(enrollment_id)',
];

async function criarSchema(db) {
  await db.run('PRAGMA foreign_keys = ON');
  for (const comando of DDL) await db.run(comando);
}

/** Carga inicial. A senha entra no banco já com hash, nunca em texto plano. */
async function semear(db) {
  const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
  if (total > 0) return false;

  await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
    'Leonan',
    'leonan@fullcycle.com.br',
    gerarHash('123'),
  ]);
  await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)', [
    'Clean Architecture',
    997.0,
    'Docker',
    497.0,
  ]);
  await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
  await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, ?)', [
    PagamentoStatus.PAGO,
  ]);
  return true;
}

async function inicializar(db, { comSeed = true } = {}) {
  await criarSchema(db);
  if (comSeed) await semear(db);
  return db;
}

module.exports = { criarSchema, semear, inicializar };
