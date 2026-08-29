import logging
from flask import jsonify, request
from src.database import db
from src.middlewares.errors import NaoEncontrado
from src.models import Category, Task, User
from src.utils import validators
from src.utils.constants import PRIORIDADE_PADRAO, STATUS_PENDENTE
log = logging.getLogger(__name__)

class TaskController:

    def __init__(self, notificador=None):
        self._notificador = notificador

    def listar(self):
        tarefas = Task.listar(com_relacionamentos=True)
        return (jsonify([t.to_dict(com_relacionamentos=True) for t in tarefas]), 200)

    def buscar(self, task_id):
        tarefa = Task.buscar(task_id)
        if not tarefa:
            return (jsonify({'error': 'Task não encontrada'}), 404)
        dados = tarefa.to_dict()
        dados['overdue'] = tarefa.is_overdue()
        return (jsonify(dados), 200)

    def criar(self):
        dados = validators.exigir_corpo(request.get_json(silent=True))
        titulo = validators.validar_titulo(dados.get('title'))
        status = validators.validar_status(dados.get('status', STATUS_PENDENTE))
        prioridade = validators.validar_prioridade(dados.get('priority', PRIORIDADE_PADRAO))
        user_id = dados.get('user_id')
        category_id = dados.get('category_id')
        if user_id and (not User.buscar(user_id)):
            raise NaoEncontrado('Usuário não encontrado')
        if category_id and (not Category.buscar(category_id)):
            raise NaoEncontrado('Categoria não encontrada')
        tarefa = Task(title=titulo, description=dados.get('description', ''), status=status, priority=prioridade, user_id=user_id, category_id=category_id, due_date=validators.converter_data(dados.get('due_date')), tags=validators.normalizar_tags(dados.get('tags')))
        db.session.add(tarefa)
        db.session.commit()
        log.info('task criada', extra={'task_id': tarefa.id})
        if self._notificador and tarefa.user:
            self._notificador.notificar_atribuicao(tarefa.user, tarefa)
        return (jsonify(tarefa.to_dict()), 201)

    def atualizar(self, task_id):
        tarefa = Task.buscar(task_id)
        if not tarefa:
            return (jsonify({'error': 'Task não encontrada'}), 404)
        dados = validators.exigir_corpo(request.get_json(silent=True))
        if 'title' in dados:
            tarefa.title = validators.validar_titulo(dados['title'], obrigatorio=False)
        if 'description' in dados:
            tarefa.description = dados['description']
        if 'status' in dados:
            tarefa.status = validators.validar_status(dados['status'])
        if 'priority' in dados:
            tarefa.priority = validators.validar_prioridade(dados['priority'])
        if 'user_id' in dados:
            if dados['user_id'] and (not User.buscar(dados['user_id'])):
                raise NaoEncontrado('Usuário não encontrado')
            tarefa.user_id = dados['user_id']
        if 'category_id' in dados:
            if dados['category_id'] and (not Category.buscar(dados['category_id'])):
                raise NaoEncontrado('Categoria não encontrada')
            tarefa.category_id = dados['category_id']
        if 'due_date' in dados:
            tarefa.due_date = validators.converter_data(dados['due_date'], mensagem='Formato de data inválido')
        if 'tags' in dados:
            tarefa.tags = validators.normalizar_tags(dados['tags'])
        db.session.commit()
        log.info('task atualizada', extra={'task_id': tarefa.id})
        return (jsonify(tarefa.to_dict()), 200)

    def remover(self, task_id):
        tarefa = Task.buscar(task_id)
        if not tarefa:
            return (jsonify({'error': 'Task não encontrada'}), 404)
        db.session.delete(tarefa)
        db.session.commit()
        log.info('task removida', extra={'task_id': task_id})
        return (jsonify({'message': 'Task deletada com sucesso'}), 200)

    def pesquisar(self):
        tarefas = Task.buscar_com_filtros(termo=request.args.get('q', ''), status=request.args.get('status', ''), prioridade=request.args.get('priority', ''), user_id=request.args.get('user_id', ''))
        return (jsonify([t.to_dict() for t in tarefas]), 200)

    def estatisticas(self):
        total = Task.total()
        por_status = Task.contagem_por_status()
        concluidas = por_status.get('done', 0)
        return (jsonify({'total': total, 'pending': por_status.get('pending', 0), 'in_progress': por_status.get('in_progress', 0), 'done': concluidas, 'cancelled': por_status.get('cancelled', 0), 'overdue': len(Task.atrasadas()), 'completion_rate': round(concluidas / total * 100, 2) if total > 0 else 0}), 200)
