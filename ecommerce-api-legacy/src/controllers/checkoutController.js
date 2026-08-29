'use strict';

const { DadosInvalidos, NaoAutorizado, NaoEncontrado, Conflito } = require('../middlewares/errors');

class CheckoutController {
  constructor({ usuarios, cursos, matriculas, pagamentos, auditoria, gateway, cache, db, logger }) {
    this.usuarios = usuarios;
    this.cursos = cursos;
    this.matriculas = matriculas;
    this.pagamentos = pagamentos;
    this.auditoria = auditoria;
    this.gateway = gateway;
    this.cache = cache;
    this.db = db;
    this.logger = logger;
  }

  static validar(corpo) {
    const { usr: nome, eml: email, pwd: senha, c_id: cursoId, card: cartao } = corpo || {};
    if (!nome || !email || !cursoId || !cartao) throw new DadosInvalidos('Bad Request');
    return { nome, email, senha, cursoId, cartao };
  }

  async resolverComprador({ nome, email, senha, cursoId }) {
    const existente = await this.usuarios.buscarPorEmail(email);
    if (!existente) {
      if (!senha) throw new DadosInvalidos('Senha é obrigatória para criar a conta');
      return { nome, email, senha, id: null };
    }

    const autenticado = await this.usuarios.autenticar(email, senha || '');
    if (!autenticado) throw new NaoAutorizado('Credenciais inválidas');
    if (await this.matriculas.jaMatriculado(autenticado.id, cursoId)) {
      throw new Conflito('Usuário já matriculado neste curso');
    }
    return autenticado;
  }

  handler() {
    return async (req, res, next) => {
      try {
        const dados = CheckoutController.validar(req.body);

        const curso = await this.cursos.buscarAtivoPorId(dados.cursoId);
        if (!curso) throw new NaoEncontrado('Curso não encontrado');

        const comprador = await this.resolverComprador(dados);

        const autorizacao = await this.gateway.autorizar({
          cartao: dados.cartao,
          valor: curso.price,
        });
        if (!autorizacao.aprovado) throw new DadosInvalidos('Pagamento recusado');

        let usuarioId;
        const enrollmentId = await this.db.transacao(async () => {
          const usuario =
            comprador.id != null
              ? comprador
              : await this.usuarios.criar({
                  nome: comprador.nome,
                  email: comprador.email,
                  senha: comprador.senha,
                });
          usuarioId = usuario.id;
          const id = await this.matriculas.criar(usuario.id, curso.id);
          await this.pagamentos.registrar(id, curso.price, autorizacao.status);
          await this.auditoria.registrar(`Checkout curso ${curso.id} por ${usuario.id}`);
          return id;
        });

        this.cache.set(`last_checkout_${usuarioId}`, curso.title);
        this.logger.info('checkout concluído', { usuarioId, cursoId: curso.id });

        return res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
      } catch (erro) {
        return next(erro);
      }
    };
  }
}

module.exports = { CheckoutController };
