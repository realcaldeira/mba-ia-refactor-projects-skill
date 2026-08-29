class BaseModel:

    def __init__(self, conexao):
        self._db = conexao

    def query_all(self, sql, params=()):
        return [dict(linha) for linha in self._db.execute(sql, params).fetchall()]

    def query_one(self, sql, params=()):
        linha = self._db.execute(sql, params).fetchone()
        return dict(linha) if linha else None

    def executar(self, sql, params=()):
        return self._db.execute(sql, params)

    def commit(self):
        self._db.commit()
