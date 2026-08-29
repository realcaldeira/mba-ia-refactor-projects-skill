from flask import jsonify
from src.models.task import agora

class HealthController:

    def __init__(self, versao, ambiente):
        self._versao = versao
        self._ambiente = ambiente

    def check(self):
        return (jsonify({'status': 'ok', 'timestamp': str(agora())}), 200)

    def index(self):
        return (jsonify({'message': 'Task Manager API', 'version': self._versao}), 200)
