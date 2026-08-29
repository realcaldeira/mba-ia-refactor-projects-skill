"""Relatórios: agregações vêm do banco, não de laços em memória."""
from datetime import timedelta

from flask import jsonify

from src.models import Category, Task, User
from src.models.task import agora
from src.utils.constants import ROTULOS_PRIORIDADE, STATUS_CONCLUIDA

JANELA_RECENTE_DIAS = 7


class ReportController:
    def resumo(self):
        por_status = Task.contagem_por_status()
        por_prioridade = Task.contagem_por_prioridade()
        atrasadas = Task.atrasadas()
        momento = agora()
        sete_dias_atras = momento - timedelta(days=JANELA_RECENTE_DIAS)
        produtividade = Task.produtividade_por_usuario(STATUS_CONCLUIDA)

        def dias_de_atraso(tarefa):
            limite = tarefa.due_date
            if limite.tzinfo is None:
                limite = limite.replace(tzinfo=momento.tzinfo)
            return (momento - limite).days

        return jsonify(
            {
                "generated_at": str(momento),
                "overview": {
                    "total_tasks": Task.total(),
                    "total_users": User.total(),
                    "total_categories": Category.total(),
                },
                "tasks_by_status": {
                    "pending": por_status.get("pending", 0),
                    "in_progress": por_status.get("in_progress", 0),
                    "done": por_status.get("done", 0),
                    "cancelled": por_status.get("cancelled", 0),
                },
                "tasks_by_priority": {
                    rotulo: por_prioridade.get(nivel, 0)
                    for nivel, rotulo in ROTULOS_PRIORIDADE.items()
                },
                "overdue": {
                    "count": len(atrasadas),
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "due_date": str(t.due_date),
                            "days_overdue": dias_de_atraso(t),
                        }
                        for t in atrasadas
                    ],
                },
                "recent_activity": {
                    "tasks_created_last_7_days": Task.criadas_desde(sete_dias_atras),
                    "tasks_completed_last_7_days": Task.concluidas_desde(
                        sete_dias_atras, STATUS_CONCLUIDA
                    ),
                },
                "user_productivity": [
                    {
                        "user_id": usuario.id,
                        "user_name": usuario.name,
                        "total_tasks": produtividade.get(usuario.id, (0, 0))[0],
                        "completed_tasks": produtividade.get(usuario.id, (0, 0))[1],
                        "completion_rate": round(
                            (produtividade.get(usuario.id, (0, 0))[1]
                             / produtividade.get(usuario.id, (0, 0))[0]) * 100,
                            2,
                        )
                        if produtividade.get(usuario.id, (0, 0))[0] > 0
                        else 0,
                    }
                    for usuario in User.listar()
                ],
            }
        ), 200

    def por_usuario(self, user_id):
        usuario = User.buscar(user_id)
        if not usuario:
            return jsonify({"error": "Usuário não encontrado"}), 404

        tarefas = Task.por_usuario(user_id)
        total = len(tarefas)
        contagem = {"done": 0, "pending": 0, "in_progress": 0, "cancelled": 0}
        alta_prioridade = 0
        atrasadas = 0

        for tarefa in tarefas:
            if tarefa.status in contagem:
                contagem[tarefa.status] += 1
            if tarefa.priority <= 2:
                alta_prioridade += 1
            if tarefa.is_overdue():
                atrasadas += 1

        return jsonify(
            {
                "user": {"id": usuario.id, "name": usuario.name, "email": usuario.email},
                "statistics": {
                    "total_tasks": total,
                    "done": contagem["done"],
                    "pending": contagem["pending"],
                    "in_progress": contagem["in_progress"],
                    "cancelled": contagem["cancelled"],
                    "overdue": atrasadas,
                    "high_priority": alta_prioridade,
                    "completion_rate": round((contagem["done"] / total) * 100, 2) if total > 0 else 0,
                },
            }
        ), 200
