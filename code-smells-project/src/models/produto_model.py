from src.middlewares.errors import DadosInvalidos
from src.models.base_model import BaseModel
CATEGORIAS_VALIDAS = ('informatica', 'moveis', 'vestuario', 'geral', 'eletronicos', 'livros')
CATEGORIA_PADRAO = 'geral'
NOME_MIN, NOME_MAX = (2, 200)
CAMPOS_PUBLICOS = ('id', 'nome', 'descricao', 'preco', 'estoque', 'categoria', 'ativo', 'criado_em')
_SELECT = 'SELECT id, nome, descricao, preco, estoque, categoria, ativo, criado_em FROM produtos'

def serializar(linha):
    return {campo: linha[campo] for campo in CAMPOS_PUBLICOS}

def validar(dados):
    if not dados:
        raise DadosInvalidos('Dados inválidos')
    for campo, rotulo in (('nome', 'Nome'), ('preco', 'Preço'), ('estoque', 'Estoque')):
        if campo not in dados:
            raise DadosInvalidos(f'{rotulo} é obrigatório')
    nome = dados['nome']
    if dados['preco'] < 0:
        raise DadosInvalidos('Preço não pode ser negativo')
    if dados['estoque'] < 0:
        raise DadosInvalidos('Estoque não pode ser negativo')
    if len(nome) < NOME_MIN:
        raise DadosInvalidos('Nome muito curto')
    if len(nome) > NOME_MAX:
        raise DadosInvalidos('Nome muito longo')
    categoria = dados.get('categoria', CATEGORIA_PADRAO)
    if categoria not in CATEGORIAS_VALIDAS:
        raise DadosInvalidos('Categoria inválida. Válidas: ' + str(list(CATEGORIAS_VALIDAS)))
    return {'nome': nome, 'descricao': dados.get('descricao', ''), 'preco': dados['preco'], 'estoque': dados['estoque'], 'categoria': categoria}

class ProdutoModel(BaseModel):

    def listar(self, pagina=None, tamanho=None):
        if pagina is None and tamanho is None:
            return [serializar(p) for p in self.query_all(_SELECT)]
        tamanho = min(max(int(tamanho or 20), 1), 100)
        offset = (max(int(pagina or 1), 1) - 1) * tamanho
        return [serializar(p) for p in self.query_all(f'{_SELECT} LIMIT ? OFFSET ?', (tamanho, offset))]

    def buscar_por_id(self, produto_id):
        linha = self.query_one(f'{_SELECT} WHERE id = ?', (produto_id,))
        return serializar(linha) if linha else None

    def criar(self, dados):
        cursor = self.executar('INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)', (dados['nome'], dados['descricao'], dados['preco'], dados['estoque'], dados['categoria']))
        self.commit()
        return cursor.lastrowid

    def atualizar(self, produto_id, dados):
        self.executar('UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?', (dados['nome'], dados['descricao'], dados['preco'], dados['estoque'], dados['categoria'], produto_id))
        self.commit()
        return True

    def remover(self, produto_id):
        self.executar('DELETE FROM produtos WHERE id = ?', (produto_id,))
        self.commit()
        return True

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        sql = f'{_SELECT} WHERE 1=1'
        params = []
        if termo:
            sql += ' AND (nome LIKE ? OR descricao LIKE ?)'
            params += [f'%{termo}%', f'%{termo}%']
        if categoria:
            sql += ' AND categoria = ?'
            params.append(categoria)
        if preco_min:
            sql += ' AND preco >= ?'
            params.append(preco_min)
        if preco_max:
            sql += ' AND preco <= ?'
            params.append(preco_max)
        return [serializar(p) for p in self.query_all(sql, params)]

    def contar(self):
        return self.query_one('SELECT COUNT(*) AS n FROM produtos')['n']
