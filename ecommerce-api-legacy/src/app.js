'use strict';

const express = require('express');

const { settings, validar } = require('./config/settings');
const { criarLogger } = require('./config/logger');
const { criarConexao } = require('./database/connection');
const { inicializar } = require('./database/schema');

const { UserModel } = require('./models/userModel');
const { CourseModel } = require('./models/courseModel');
const { EnrollmentModel } = require('./models/enrollmentModel');
const { PaymentModel } = require('./models/paymentModel');
const { AuditLogModel } = require('./models/auditLogModel');

const { PaymentGateway } = require('./services/paymentGateway');
const { Cache } = require('./services/cache');

const { CheckoutController } = require('./controllers/checkoutController');
const { ReportController } = require('./controllers/reportController');
const { UserController } = require('./controllers/userController');

const { registrarRotas } = require('./views/routes');
const { criarErrorHandler, rotaNaoEncontrada } = require('./middlewares/errorHandler');

/** Composition root: cria as dependências concretas e as conecta. */
async function buildApp({ config = settings, db = null, gateway = null, logger = null } = {}) {
  validar(config);

  const log = logger || criarLogger(config.logLevel);
  const conexao = db || criarConexao(config.dbPath);
  await inicializar(conexao, { comSeed: config.seedOnBoot });

  const usuarios = new UserModel(conexao);
  const cursos = new CourseModel(conexao);
  const matriculas = new EnrollmentModel(conexao);
  const pagamentos = new PaymentModel(conexao);
  const auditoria = new AuditLogModel(conexao);
  const cache = new Cache();

  const controllers = {
    checkout: new CheckoutController({
      usuarios,
      cursos,
      matriculas,
      pagamentos,
      auditoria,
      gateway: gateway || new PaymentGateway({ chave: config.payment.gatewayKey, logger: log }),
      cache,
      db: conexao,
      logger: log,
    }),
    relatorio: new ReportController({ matriculas }),
    usuario: new UserController({ usuarios, logger: log }),
  };

  const app = express();
  app.use(express.json());
  registrarRotas(app, controllers);
  app.use(rotaNaoEncontrada);
  app.use(criarErrorHandler(log));

  return { app, db: conexao, logger: log };
}

async function main() {
  const log = criarLogger(settings.logLevel);
  try {
    const { app } = await buildApp({ logger: log });
    app.listen(settings.port, settings.host, () => {
      log.info('LMS API no ar', { host: settings.host, port: settings.port });
    });
  } catch (erro) {
    log.error('falha ao iniciar a aplicação', { mensagem: erro.message });
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { buildApp };
