import sqlite3
import threading
TIMEOUT_LOCK_SEGUNDOS = 10.0

def criar_conexao(caminho):
    conexao = sqlite3.connect(caminho, timeout=TIMEOUT_LOCK_SEGUNDOS)
    conexao.row_factory = sqlite3.Row
    conexao.execute('PRAGMA foreign_keys = ON')
    return conexao

class ConexaoPorThread:

    def __init__(self, caminho, fabrica=criar_conexao):
        self._caminho = caminho
        self._fabrica = fabrica
        self._local = threading.local()

    @property
    def conexao(self):
        conexao = getattr(self._local, 'conexao', None)
        if conexao is None:
            conexao = self._fabrica(self._caminho)
            self._local.conexao = conexao
        return conexao

    def execute(self, sql, params=()):
        return self.conexao.execute(sql, params)

    def executemany(self, sql, params):
        return self.conexao.executemany(sql, params)

    def commit(self):
        self.conexao.commit()

    def __enter__(self):
        return self.conexao.__enter__()

    def __exit__(self, tipo, valor, traco):
        return self.conexao.__exit__(tipo, valor, traco)
