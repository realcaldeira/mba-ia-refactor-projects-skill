from werkzeug.security import generate_password_hash
import hashlib
import os

def seed_password():
    env = os.getenv('SEED_PASSWORD')
    if env and env.strip():
        return env.strip()
    return hashlib.sha256(b'desafio-skills-local-seed').hexdigest()[:16]

DDL = ("\n    CREATE TABLE IF NOT EXISTS produtos (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        nome TEXT NOT NULL,\n        descricao TEXT DEFAULT '',\n        preco REAL NOT NULL,\n        estoque INTEGER NOT NULL DEFAULT 0,\n        categoria TEXT NOT NULL DEFAULT 'geral',\n        ativo INTEGER NOT NULL DEFAULT 1,\n        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n    )\n    ", "\n    CREATE TABLE IF NOT EXISTS usuarios (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        nome TEXT NOT NULL,\n        email TEXT NOT NULL UNIQUE,\n        senha TEXT NOT NULL,\n        tipo TEXT NOT NULL DEFAULT 'cliente',\n        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n    )\n    ", "\n    CREATE TABLE IF NOT EXISTS pedidos (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),\n        status TEXT NOT NULL DEFAULT 'pendente',\n        total REAL NOT NULL DEFAULT 0,\n        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n    )\n    ", '\n    CREATE TABLE IF NOT EXISTS itens_pedido (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        pedido_id INTEGER NOT NULL REFERENCES pedidos(id),\n        produto_id INTEGER NOT NULL REFERENCES produtos(id),\n        quantidade INTEGER NOT NULL,\n        preco_unitario REAL NOT NULL\n    )\n    ', 'CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria)', 'CREATE INDEX IF NOT EXISTS idx_pedidos_usuario ON pedidos(usuario_id)', 'CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens_pedido(pedido_id)')
PRODUTOS_INICIAIS = (('Notebook Gamer', 'Notebook potente para jogos', 5999.99, 10, 'informatica'), ('Mouse Wireless', 'Mouse sem fio ergonômico', 89.9, 50, 'informatica'), ('Teclado Mecânico', 'Teclado mecânico RGB', 299.9, 30, 'informatica'), ("Monitor 27''", 'Monitor 27 polegadas 144hz', 1899.9, 15, 'informatica'), ('Headset Gamer', 'Headset com microfone', 199.9, 25, 'informatica'), ('Cadeira Gamer', 'Cadeira ergonômica', 1299.9, 8, 'moveis'), ('Webcam HD', 'Webcam 1080p', 249.9, 20, 'informatica'), ('Hub USB', 'Hub USB 3.0 7 portas', 79.9, 40, 'informatica'), ('SSD 1TB', 'SSD NVMe 1TB', 449.9, 35, 'informatica'), ('Camiseta Dev', 'Camiseta estampa código', 59.9, 100, 'vestuario'))
USUARIOS_INICIAIS = (('Admin', 'admin@loja.com', 'admin'), ('João Silva', 'joao@email.com', 'cliente'), ('Maria Santos', 'maria@email.com', 'cliente'))

def criar_schema(conexao):
    for comando in DDL:
        conexao.execute(comando)
    conexao.commit()

def semear(conexao):
    if conexao.execute('SELECT COUNT(*) AS n FROM produtos').fetchone()['n']:
        return False
    conexao.executemany('INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)', PRODUTOS_INICIAIS)
    credencial = seed_password()
    conexao.executemany('INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)', [(nome, email, generate_password_hash(credencial), tipo) for nome, email, tipo in USUARIOS_INICIAIS])
    conexao.commit()
    return True

def inicializar(conexao):
    criar_schema(conexao)
    semear(conexao)
    return conexao
