"""Notificações.

O transporte é injetado: a implementação padrão apenas registra em log, e a de SMTP recebe as
credenciais da config — antes elas estavam fixas no construtor e o serviço nunca era usado.
"""
import logging
import smtplib

log = logging.getLogger(__name__)


class TransporteLog:
    """Padrão em desenvolvimento: não envia nada, registra a intenção."""

    def enviar(self, destinatario, assunto, corpo):
        log.info("e-mail simulado", extra={"para": destinatario, "assunto": assunto})
        return True


class TransporteSmtp:
    def __init__(self, host, porta, usuario, senha):
        self._host, self._porta = host, porta
        self._usuario, self._senha = usuario, senha

    def enviar(self, destinatario, assunto, corpo):
        try:
            with smtplib.SMTP(self._host, self._porta) as servidor:
                servidor.starttls()
                servidor.login(self._usuario, self._senha)
                servidor.sendmail(self._usuario, destinatario, f"Subject: {assunto}\n\n{corpo}")
            return True
        except OSError as erro:
            log.error("falha ao enviar e-mail: %s", erro)
            return False


class NotificationService:
    def __init__(self, transporte=None):
        self._transporte = transporte or TransporteLog()
        self.notificacoes = []

    def notificar_atribuicao(self, usuario, tarefa):
        self._transporte.enviar(
            usuario.email,
            f"Nova task atribuída: {tarefa.title}",
            f"Olá {usuario.name},\n\nA task '{tarefa.title}' foi atribuída a você.\n\n"
            f"Prioridade: {tarefa.priority}\nStatus: {tarefa.status}",
        )
        self.notificacoes.append({"tipo": "task_assigned", "user_id": usuario.id, "task_id": tarefa.id})

    def notificar_atraso(self, usuario, tarefa):
        self._transporte.enviar(
            usuario.email,
            f"Task atrasada: {tarefa.title}",
            f"Olá {usuario.name},\n\nA task '{tarefa.title}' está atrasada!\n\n"
            f"Data limite: {tarefa.due_date}",
        )

    def listar(self, user_id):
        return [n for n in self.notificacoes if n["user_id"] == user_id]
