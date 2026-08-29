import logging
import smtplib
log = logging.getLogger(__name__)

class TransporteLog:

    def enviar(self, destinatario, assunto, corpo):
        log.info('e-mail simulado', extra={'para': destinatario, 'assunto': assunto})
        return True

class TransporteSmtp:

    def __init__(self, host, porta, usuario, senha):
        self._host, self._porta = (host, porta)
        self._usuario, self._senha = (usuario, senha)

    def enviar(self, destinatario, assunto, corpo):
        try:
            with smtplib.SMTP(self._host, self._porta) as servidor:
                servidor.starttls()
                servidor.login(self._usuario, self._senha)
                servidor.sendmail(self._usuario, destinatario, f'Subject: {assunto}\n\n{corpo}')
            return True
        except OSError as erro:
            log.error('falha ao enviar e-mail: %s', erro)
            return False

class NotificationService:

    def __init__(self, transporte=None):
        self._transporte = transporte or TransporteLog()
        self.notificacoes = []

    def notificar_atribuicao(self, usuario, tarefa):
        self._transporte.enviar(usuario.email, f'Nova task atribuída: {tarefa.title}', f"Olá {usuario.name},\n\nA task '{tarefa.title}' foi atribuída a você.\n\nPrioridade: {tarefa.priority}\nStatus: {tarefa.status}")
        self.notificacoes.append({'tipo': 'task_assigned', 'user_id': usuario.id, 'task_id': tarefa.id})

    def notificar_atraso(self, usuario, tarefa):
        self._transporte.enviar(usuario.email, f'Task atrasada: {tarefa.title}', f"Olá {usuario.name},\n\nA task '{tarefa.title}' está atrasada!\n\nData limite: {tarefa.due_date}")

    def listar(self, user_id):
        return [n for n in self.notificacoes if n['user_id'] == user_id]
