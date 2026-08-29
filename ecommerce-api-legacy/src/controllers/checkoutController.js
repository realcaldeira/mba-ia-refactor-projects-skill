'use strict';

const { DadosInvalidos, NaoAutorizado, NaoEncontrado } = require('../middlewares/errors');

/**
 * Caso de uso: matricular um aluno em um curso e cobrar.
 * Orquestra models e o gateway; não contém SQL nem monta query.
 */
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

  /**
   * Resolve a identidade do comprador.
   * Antes, um e-mail já cadastrado bastava para comprar em nome do titular: a senha só era
   * usada na criação. Agora, usuário existente precisa autenticar.
   */
  async resolverUsuario({ nome, email, senha }) {
    const existente = await this.usuarios.buscarPorEmail(email);
    if (!existente) {
      if (!senha) throw new DadosInvalidos('Senha é obrigatória para criar a conta');
      return this.usuarios.criar({ nome, email, senha });
    }

    const autenticado = await this.usuarios.autenticar(email, senha || '');
    if (!autenticado) throw new NaoAutorizado('Credenciais inválidas');
    return autenticado;
  }

  handler() {
    return async (req, res, next) => {
      try {
        const dados = CheckoutController.validar(req.body);

        const curso = await this.cursos.buscarAtivoPorId(dados.cursoId);
        if (!curso) throw new NaoEncontrado('Curso não encontrado');

        const usuario = await this.resolverUsuario(dados);

        const autorizacao = await this.gateway.autorizar({
          cartao: dados.cartao,
          valor: curso.price,
        });
        if (!autorizacao.aprovado) throw new DadosInvalidos('Pagamento recusado');

        // Matrícula, pagamento e auditoria em uma unidade de trabalho.
        const enrollmentId = await this.db.transacao(async () => {
          const id = await this.matriculas.criar(usuario.id, curso.id);
          await this.pagamentos.registrar(id, curso.price, autorizacao.status);
          await this.auditoria.registrar(`Checkout curso ${curso.id} por ${usuario.id}`);
          return id;
        });

        this.cache.set(`last_checkout_${usuario.id}`, curso.title);
        this.logger.info('checkout concluído', { usuarioId: usuario.id, cursoId: curso.id });

        return res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
      } catch (erro) {
        return next(erro);
      }
    };
  }
}

module.exports = { CheckoutController };
