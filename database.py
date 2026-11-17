import sqlite3
import re
import difflib
import unicodedata

NOME_BANCO = "banco_dados.db"

def conectar():
    return sqlite3.connect(NOME_BANCO)

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()
    
    # Tabela de orçamentos e pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefone TEXT,
            endereco TEXT,
            data_evento TEXT,
            orcamento TEXT,
            tipo TEXT DEFAULT 'Orcamento',
            distancia_km REAL DEFAULT 0.0,
            desconto REAL DEFAULT 0.0,
            observacoes TEXT
        )
    """)

    # Tabela de Catálogo e Estoque
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            nome TEXT NOT NULL,
            unidade TEXT DEFAULT 'Unidade',
            preco REAL DEFAULT 0.0,
            estoque_total INTEGER DEFAULT 0,
            fotos TEXT DEFAULT '[]'
        )
    """)

    # Migrações automáticas para manter compatibilidade
    try:
        cursor.execute("ALTER TABLE orcamentos ADD COLUMN distancia_km REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE orcamentos ADD COLUMN desconto REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE orcamentos ADD COLUMN observacoes TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE catalogo ADD COLUMN fotos TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass

    # Tabela de Clientes (evita cadastrar o mesmo cliente de formas diferentes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            endereco TEXT
        )
    """)

    conn.commit()

    # Importa clientes já existentes nos pedidos na primeira execução
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT cliente, telefone, endereco FROM orcamentos ORDER BY id ASC")
        for nome, tel, end in cursor.fetchall():
            _registrar_cliente_cursor(cursor, nome, tel, end)
        conn.commit()

    conn.close()
    
    popular_catalogo_inicial()


# ---------------------------------------------------------------------------
# CONTROLE DE CLIENTES
# ---------------------------------------------------------------------------
def _normalizar_nome(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.lower().split())

def _somente_digitos(texto):
    return re.sub(r"\D", "", texto or "")

def _achar_cliente_cursor(cursor, nome, telefone):
    """Retorna a linha (id, nome, telefone, endereco) do cliente equivalente, ou None."""
    cursor.execute("SELECT id, nome, telefone, endereco FROM clientes")
    todos = cursor.fetchall()

    tel = _somente_digitos(telefone)
    if len(tel) >= 8:
        for row in todos:
            t = _somente_digitos(row[2])
            if len(t) >= 8 and t[-8:] == tel[-8:]:
                return row

    nome_norm = _normalizar_nome(nome)
    if nome_norm:
        for row in todos:
            if _normalizar_nome(row[1]) == nome_norm:
                return row
    return None

def _registrar_cliente_cursor(cursor, nome, telefone, endereco):
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        return None

    existente = _achar_cliente_cursor(cursor, nome, telefone)
    if existente:
        id_cli, _, tel_atual, end_atual = existente
        novo_tel = tel_atual if (tel_atual or "").strip() else telefone
        novo_end = endereco or end_atual
        cursor.execute("UPDATE clientes SET telefone = ?, endereco = ? WHERE id = ?", (novo_tel, novo_end, id_cli))
        return id_cli

    cursor.execute("INSERT INTO clientes (nome, telefone, endereco) VALUES (?, ?, ?)", (nome, telefone, endereco))
    return cursor.lastrowid

def registrar_cliente(nome, telefone, endereco=""):
    conn = conectar()
    cursor = conn.cursor()
    id_cli = _registrar_cliente_cursor(cursor, nome, telefone, endereco)
    conn.commit()
    conn.close()
    return id_cli

def buscar_clientes(termo, limite=8):
    """Filtro automático por parte do nome (todas as palavras digitadas) ou parte do telefone."""
    termo = (termo or "").strip()
    if not termo:
        return []

    palavras = _normalizar_nome(termo).split()
    digitos = _somente_digitos(termo)
    # Se o termo é majoritariamente numérico, busca por telefone
    busca_telefone = len(digitos) >= 2 and len(digitos) >= len(termo.replace(" ", "")) - 2

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, telefone, endereco FROM clientes ORDER BY nome COLLATE NOCASE")
    todos = cursor.fetchall()
    conn.close()

    resultado = []
    for row in todos:
        if busca_telefone:
            if digitos in _somente_digitos(row[2]):
                resultado.append(row)
        else:
            nome_norm = _normalizar_nome(row[1])
            if all(p in nome_norm for p in palavras):
                resultado.append(row)
        if len(resultado) >= limite:
            break
    return resultado

def listar_clientes(filtro=""):
    """Lista todos os clientes (opcionalmente filtrando por nome ou parte do telefone)."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, telefone, endereco FROM clientes ORDER BY nome COLLATE NOCASE")
    todos = cursor.fetchall()
    conn.close()

    filtro = (filtro or "").strip()
    if not filtro:
        return todos

    palavras = _normalizar_nome(filtro).split()
    digitos = _somente_digitos(filtro)
    resultado = []
    for row in todos:
        nome_norm = _normalizar_nome(row[1])
        if all(p in nome_norm for p in palavras) or (digitos and digitos in _somente_digitos(row[2])):
            resultado.append(row)
    return resultado

def salvar_cliente(id_cliente, nome, telefone, endereco):
    """Cria ou edita um cliente. Retorna (ok, mensagem)."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        return False, "Informe o nome do cliente."

    conn = conectar()
    cursor = conn.cursor()

    existente = _achar_cliente_cursor(cursor, nome, telefone)
    if existente and existente[0] != id_cliente:
        conn.close()
        return False, f"Já existe um cliente cadastrado com esse nome/telefone:\n\n{existente[1]}  |  {existente[2] or 'sem telefone'}"

    if id_cliente:
        cursor.execute("UPDATE clientes SET nome = ?, telefone = ?, endereco = ? WHERE id = ?",
                       (nome, telefone, endereco, id_cliente))
    else:
        cursor.execute("INSERT INTO clientes (nome, telefone, endereco) VALUES (?, ?, ?)",
                       (nome, telefone, endereco))
    conn.commit()
    conn.close()
    return True, "Cliente salvo com sucesso!"

def excluir_cliente(id_cliente):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = ?", (id_cliente,))
    conn.commit()
    conn.close()

def encontrar_cliente_similar(nome, telefone):
    """Procura cliente cadastrado equivalente (mesmo telefone, nome igual ou nome muito parecido)."""
    conn = conectar()
    cursor = conn.cursor()
    achado = _achar_cliente_cursor(cursor, nome, telefone)
    if not achado:
        nome_norm = _normalizar_nome(nome)
        if nome_norm:
            cursor.execute("SELECT id, nome, telefone, endereco FROM clientes")
            melhor, melhor_score = None, 0.0
            for row in cursor.fetchall():
                score = difflib.SequenceMatcher(None, nome_norm, _normalizar_nome(row[1])).ratio()
                if score > melhor_score:
                    melhor, melhor_score = row, score
            if melhor_score >= 0.85:
                achado = melhor
    conn.close()
    return achado

def popular_catalogo_inicial():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM catalogo")
    qtd = cursor.fetchone()[0]

    if qtd == 0:
        itens_iniciais = [
            ("MOBILIÁRIO & MESAS", "Jogo de Mesa com Cadeiras de Plástico (Branca)", "Jogo", 14.00, 50),
            ("MOBILIÁRIO & MESAS", "Mesa Redonda de 6 Lugares (com tampão de madeira)", "Unidade", 18.00, 20),
            ("MOBILIÁRIO & MESAS", "Mesa Redonda de 7 Lugares (com tampão de madeira)", "Unidade", 20.00, 20),
            ("MOBILIÁRIO & MESAS", "Aparador de Madeira (2,50m x 0,80m)", "Unidade", 25.00, 5),
            ("TOALHAS & ENXOVAL", "Toalha Quadrada para 4 Lugares (1,50m x 1,50m)", "Unidade", 6.00, 100),
            ("TOALHAS & ENXOVAL", "Toalha Redonda para 6 e 7 Lugares (Cor Lisa)", "Unidade", 12.00, 80),
            ("TOALHAS & ENXOVAL", "Toalha para Aparador", "Unidade", 25.00, 10),
            ("LOUÇAS, TALHERES & COPOS", "Prataria (Prato, Garfo e Faca de Jantar/Sobremesa)", "Unidade", 0.80, 300),
            ("LOUÇAS, TALHERES & COPOS", "Copo Tradicional", "Unidade", 0.80, 300),
            ("LOUÇAS, TALHERES & COPOS", "Taça para Água / Flauta", "Unidade", 1.00, 200),
            ("LOUÇAS, TALHERES & COPOS", "Taça Colorida", "Unidade", 1.50, 150),
            ("SERVIÇO & RECHAUDS", "Rechaud Redondo", "Unidade", 25.00, 10),
            ("SERVIÇO & RECHAUDS", "Rechaud Quadrado 9 Litros", "Unidade", 40.00, 10),
            ("SERVIÇO & RECHAUDS", "Bandeja Oval Média", "Unidade", 10.00, 15),
            ("SERVIÇO & RECHAUDS", "Bandeja Oval Grande", "Unidade", 15.00, 15),
            ("SERVIÇO & RECHAUDS", "Bandeja para Garçom", "Unidade", 10.00, 10),
            ("SERVIÇO & RECHAUDS", "Pegador / Colher para Arroz ou Feijão Tropeiro", "Unidade", 7.00, 20),
            ("SERVIÇO & RECHAUDS", "Jarra em Inox", "Unidade", 10.00, 15),
            ("SERVIÇO & RECHAUDS", "Lixeira Redonda 7 Litros", "Unidade", 25.00, 10),
            ("EQUIPAMENTOS", "Freezer Horizontal Branca 2 Tampas (400 Litros)", "Diária", 200.00, 3),
            ("EQUIPAMENTOS", "Freezer Horizontal Branca 2 Tampas (500 Litros)", "Diária", 250.00, 2)
        ]
        cursor.executemany("""
            INSERT INTO catalogo (categoria, nome, unidade, preco, estoque_total)
            VALUES (?, ?, ?, ?, ?)
        """, itens_iniciais)
        conn.commit()

    conn.close()

def buscar_catalogo():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, categoria, nome, unidade, preco, estoque_total, fotos FROM catalogo ORDER BY categoria, nome")
    rows = cursor.fetchall()
    conn.close()
    return rows

def salvar_item_catalogo(id_item, categoria, nome, unidade, preco, estoque, fotos=None):
    import json
    conn = conectar()
    cursor = conn.cursor()
    if id_item:
        if fotos is None:
            cursor.execute("""
                UPDATE catalogo
                SET categoria=?, nome=?, unidade=?, preco=?, estoque_total=?
                WHERE id=?
            """, (categoria, nome, unidade, preco, estoque, id_item))
        else:
            fotos_json = json.dumps(fotos, ensure_ascii=False)
            cursor.execute("""
                UPDATE catalogo
                SET categoria=?, nome=?, unidade=?, preco=?, estoque_total=?, fotos=?
                WHERE id=?
            """, (categoria, nome, unidade, preco, estoque, fotos_json, id_item))
    else:
        if fotos is None:
            fotos = []
        fotos_json = json.dumps(fotos, ensure_ascii=False)
        cursor.execute("""
            INSERT INTO catalogo (categoria, nome, unidade, preco, estoque_total, fotos)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (categoria, nome, unidade, preco, estoque, fotos_json))
    conn.commit()
    conn.close()

def excluir_item_catalogo(id_item):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM catalogo WHERE id=?", (id_item,))
    conn.commit()
    conn.close()

def salvar_fotos_item_catalogo(id_item, fotos):
    import json
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE catalogo SET fotos=? WHERE id=?", (json.dumps(fotos or [], ensure_ascii=False), id_item))
    conn.commit()
    conn.close()

def obter_fotos_item_catalogo(id_item):
    import json
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT fotos FROM catalogo WHERE id=?", (id_item,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return []
    try:
        return json.loads(row[0])
    except Exception:
        return []

def inserir_pedido(dados, tipo="Orcamento"):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orcamentos (cliente, telefone, endereco, data_evento, orcamento, tipo, distancia_km, desconto, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get("cliente", ""),
        dados.get("telefone", ""),
        dados.get("endereco", ""),
        dados.get("data_evento", ""),
        dados.get("orcamento", ""),
        tipo,
        float(dados.get("distancia_km", 0.0) or 0.0),
        float(dados.get("desconto", 0.0) or 0.0),
        dados.get("observacoes", "")
    ))
    novo_id = cursor.lastrowid
    _registrar_cliente_cursor(cursor, dados.get("cliente"), dados.get("telefone"), dados.get("endereco"))
    conn.commit()
    conn.close()
    return novo_id

def atualizar_pedido(id_pedido, dados):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orcamentos
        SET cliente = ?, telefone = ?, endereco = ?, data_evento = ?, orcamento = ?, distancia_km = ?, desconto = ?, observacoes = ?
        WHERE id = ?
    """, (
        dados.get("cliente", ""),
        dados.get("telefone", ""),
        dados.get("endereco", ""),
        dados.get("data_evento", ""),
        dados.get("orcamento", ""),
        float(dados.get("distancia_km", 0.0) or 0.0),
        float(dados.get("desconto", 0.0) or 0.0),
        dados.get("observacoes", ""),
        id_pedido
    ))
    _registrar_cliente_cursor(cursor, dados.get("cliente"), dados.get("telefone"), dados.get("endereco"))
    conn.commit()
    conn.close()

def alterar_status(id_pedido, novo_status):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE orcamentos SET tipo = ? WHERE id = ?", (novo_status, id_pedido))
    conn.commit()
    conn.close()

def alterar_status_multiplos(lista_ids, novo_status):
    if not lista_ids:
        return
    conn = conectar()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in lista_ids)
    cursor.execute(f"UPDATE orcamentos SET tipo = ? WHERE id IN ({placeholders})", [novo_status] + list(lista_ids))
    conn.commit()
    conn.close()

def buscar_por_status(status):
    conn = conectar()
    cursor = conn.cursor()
    if status == 'Pedido':
        cursor.execute("""
            SELECT id, cliente, telefone, endereco, data_evento, tipo 
            FROM orcamentos 
            WHERE tipo IN ('Pedido', 'Ja Entregue', 'Ja Recolhido', 'Arquivado') 
            ORDER BY id DESC
        """)
    else:
        cursor.execute("SELECT id, cliente, telefone, endereco, data_evento, tipo FROM orcamentos WHERE tipo = ? ORDER BY id DESC", (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def buscar_todos_pedidos_relatorio():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cliente, telefone, endereco, data_evento, orcamento, tipo, distancia_km, desconto, observacoes 
        FROM orcamentos
    """)
    rows = cursor.fetchall()
    conn.close()
    
    pedidos = []
    for r in rows:
        pedidos.append({
            "id": r[0], "cliente": r[1], "telefone": r[2],
            "endereco": r[3], "data_evento": r[4], "orcamento": r[5],
            "tipo": r[6], "distancia_km": r[7] or 0.0,
            "desconto": r[8] or 0.0, "observacoes": r[9] or ""
        })
    return pedidos

def buscar_por_id(id_pedido):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cliente, telefone, endereco, data_evento, orcamento, tipo, distancia_km, desconto, observacoes 
        FROM orcamentos WHERE id = ?
    """, (id_pedido,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "cliente": row[1], "telefone": row[2],
            "endereco": row[3], "data_evento": row[4], "orcamento": row[5], 
            "tipo": row[6], 
            "distancia_km": row[7] if len(row) > 7 and row[7] is not None else 0.0,
            "desconto": row[8] if len(row) > 8 and row[8] is not None else 0.0,
            "observacoes": row[9] if len(row) > 9 and row[9] is not None else ""
        }
    return None
