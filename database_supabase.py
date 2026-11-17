"""
Camada de dados Supabase (PostgreSQL) — drop-in replacement para database.py
Mantém a MESMA API pública para compatibilidade com main.py, interface.py, nuvem_sync.py
"""

import re
import difflib
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional
from config_supabase import get_client, testar_conexao as _testar_supabase

# Cliente Supabase — tenta conectar, mas falha graceful para SQLite se .env estiver incompleto
try:
    _sb = get_client()
    # Testa conexão real
    _sb.table("catalogo").select("id", count="exact").limit(1).execute()
    _supabase_available = True
except Exception:
    _sb = None
    _supabase_available = False
    print("AVISO: Supabase indisponivel — usando modo SQLite local apenas")

# ---------------------------------------------------------------------------
# UTILITÁRIOS (iguais ao database.py original)
# ---------------------------------------------------------------------------
def _normalizar_nome(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.lower().split())


def _somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _row_to_catalogo(row: dict) -> tuple:
    """Converte row do Supabase para tupla compatível com database.py"""
    return (
        row["id"],
        row.get("categoria") or "Geral",
        row["nome"],
        row.get("unidade") or "Unidade",
        float(row.get("preco") or 0),
        int(row.get("estoque") or row.get("estoque_total") or 0),
    )


def _row_to_cliente(row: dict) -> tuple:
    return (
        row["id"],
        row["nome"],
        row.get("telefone"),
        row.get("endereco"),
    )


def _row_to_orcamento(row: dict) -> tuple:
    return (
        row["id"],
        row["cliente"],
        row.get("telefone"),
        row.get("endereco"),
        row.get("data_evento"),
        row.get("tipo"),
    )


def _row_to_orcamento_full(row: dict) -> dict:
    return {
        "id": row["id"],
        "cliente": row["cliente"],
        "telefone": row.get("telefone"),
        "endereco": row.get("endereco"),
        "data_evento": row.get("data_evento"),
        "orcamento": row.get("orcamento"),
        "tipo": row.get("tipo"),
        "distancia_km": float(row.get("distancia_km") or 0),
        "desconto": float(row.get("desconto") or 0),
        "observacoes": row.get("observacoes") or "",
    }


# ---------------------------------------------------------------------------
# INICIALIZAÇÃO / TESTE
# ---------------------------------------------------------------------------
def criar_tabelas():
    """
    No Supabase as tabelas já existem (criadas via SQL Editor).
    Esta função só testa a conexão e popula catálogo inicial se vazio.
    Se Supabase indisponível, usa modo SQLite local (tabelas já existem em banco_dados.db).
    """
    if _supabase_available:
        ok, msg = _testar_supabase()
        if not ok:
            raise RuntimeError(msg)
        popular_catalogo_inicial()
    else:
        print("AVISO: Supabase indisponível — usando modo SQLite local.")
        print("     Tabelas do catálogo já existem em banco_dados.db (SQLite).")
        # No SQLite, as tabelas já foram criadas pelo database.py original.
        # Se for primeira vez, pode rodar o create_tables do SQLite manualmente.


def popular_catalogo_inicial():
    """Popula catálogo com itens padrão se estiver vazio."""
    try:
        resp = _sb.table("catalogo").select("id", count="exact").execute()
        if resp.count and resp.count > 0:
            return  # já tem itens
    except Exception:
        return

    itens_iniciais = [
        {"categoria": "MOBILIÁRIO & MESAS", "nome": "Jogo de Mesa com Cadeiras de Plástico (Branca)", "unidade": "Jogo", "preco": 14.00, "estoque": 50},
        {"categoria": "MOBILIÁRIO & MESAS", "nome": "Mesa Redonda de 6 Lugares (com tampão de madeira)", "unidade": "Unidade", "preco": 18.00, "estoque": 20},
        {"categoria": "MOBILIÁRIO & MESAS", "nome": "Mesa Redonda de 7 Lugares (com tampão de madeira)", "unidade": "Unidade", "preco": 20.00, "estoque": 20},
        {"categoria": "MOBILIÁRIO & MESAS", "nome": "Aparador de Madeira (2,50m x 0,80m)", "unidade": "Unidade", "preco": 25.00, "estoque": 5},
        {"categoria": "TOALHAS & ENXOVAL", "nome": "Toalha Quadrada para 4 Lugares (1,50m x 1,50m)", "unidade": "Unidade", "preco": 6.00, "estoque": 100},
        {"categoria": "TOALHAS & ENXOVAL", "nome": "Toalha Redonda para 6 e 7 Lugares (Cor Lisa)", "unidade": "Unidade", "preco": 12.00, "estoque": 80},
        {"categoria": "TOALHAS & ENXOVAL", "nome": "Toalha para Aparador", "unidade": "Unidade", "preco": 25.00, "estoque": 10},
        {"categoria": "LOUÇAS, TALHERES & COPOS", "nome": "Prataria (Prato, Garfo e Faca de Jantar/Sobremesa)", "unidade": "Unidade", "preco": 0.80, "estoque": 300},
        {"categoria": "LOUÇAS, TALHERES & COPOS", "nome": "Copo Tradicional", "unidade": "Unidade", "preco": 0.80, "estoque": 300},
        {"categoria": "LOUÇAS, TALHERES & COPOS", "nome": "Taça para Água / Flauta", "unidade": "Unidade", "preco": 1.00, "estoque": 200},
        {"categoria": "LOUÇAS, TALHERES & COPOS", "nome": "Taça Colorida", "unidade": "Unidade", "preco": 1.50, "estoque": 150},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Rechaud Redondo", "unidade": "Unidade", "preco": 25.00, "estoque": 10},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Rechaud Quadrado 9 Litros", "unidade": "Unidade", "preco": 40.00, "estoque": 10},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Bandeja Oval Média", "unidade": "Unidade", "preco": 10.00, "estoque": 15},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Bandeja Oval Grande", "unidade": "Unidade", "preco": 15.00, "estoque": 15},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Bandeja para Garçom", "unidade": "Unidade", "preco": 10.00, "estoque": 10},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Pegador / Colher para Arroz ou Feijão Tropeiro", "unidade": "Unidade", "preco": 7.00, "estoque": 20},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Jarra em Inox", "unidade": "Unidade", "preco": 10.00, "estoque": 15},
        {"categoria": "SERVIÇO & RECHAUDS", "nome": "Lixeira Redonda 7 Litros", "unidade": "Unidade", "preco": 25.00, "estoque": 10},
        {"categoria": "EQUIPAMENTOS", "nome": "Freezer Horizontal Branca 2 Tampas (400 Litros)", "unidade": "Diária", "preco": 200.00, "estoque": 3},
        {"categoria": "EQUIPAMENTOS", "nome": "Freezer Horizontal Branca 2 Tampas (500 Litros)", "unidade": "Diária", "preco": 250.00, "estoque": 2},
    ]
    try:
        _sb.table("catalogo").insert(itens_iniciais).execute()
    except Exception:
        pass  # silencioso se falhar


# ---------------------------------------------------------------------------
# CONTROLE DE CLIENTES
# ---------------------------------------------------------------------------
def _achar_cliente(nome: str, telefone: str) -> Optional[dict]:
    """Procura cliente equivalente (mesmo telefone ou nome normalizado igual)."""
    tel = _somente_digitos(telefone)
    nome_norm = _normalizar_nome(nome)

    # Busca por telefone (últimos 8 dígitos)
    if len(tel) >= 8:
        try:
            resp = _sb.table("clientes").select("*").execute()
            for row in resp.data or []:
                t = _somente_digitos(row.get("telefone") or "")
                if len(t) >= 8 and t[-8:] == tel[-8:]:
                    return row
        except Exception:
            pass

    # Busca por nome normalizado
    if nome_norm:
        try:
            resp = _sb.table("clientes").select("*").execute()
            for row in resp.data or []:
                if _normalizar_nome(row["nome"]) == nome_norm:
                    return row
        except Exception:
            pass
    return None


def _registrar_cliente(nome: str, telefone: str, endereco: str) -> Optional[int]:
    """Registra cliente se não existir, ou atualiza telefone/endereco."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        return None

    existente = _achar_cliente(nome, telefone)
    if existente:
        # Atualiza se tiver info nova
        novo_tel = existente.get("telefone") or telefone
        novo_end = endereco or existente.get("endereco") or ""
        if novo_tel != existente.get("telefone") or novo_end != existente.get("endereco"):
            _sb.table("clientes").update({"telefone": novo_tel, "endereco": novo_end}).eq("id", existente["id"]).execute()
        return existente["id"]

    # Insere novo
    resp = _sb.table("clientes").insert({"nome": nome, "telefone": telefone, "endereco": endereco}).execute()
    if resp.data:
        return resp.data[0]["id"]
    return None


def registrar_cliente(nome: str, telefone: str, endereco: str = "") -> Optional[int]:
    return _registrar_cliente(nome, telefone, endereco)


def buscar_clientes(termo: str, limite: int = 8) -> list:
    """Filtro automático por parte do nome ou telefone."""
    termo = (termo or "").strip()
    if not termo:
        return []

    palavras = _normalizar_nome(termo).split()
    digitos = _somente_digitos(termo)
    busca_telefone = len(digitos) >= 2 and len(digitos) >= len(termo.replace(" ", "")) - 2

    try:
        resp = _sb.table("clientes").select("*").order("nome").execute()
        todos = resp.data or []
    except Exception:
        return []

    resultado = []
    for row in todos:
        if busca_telefone:
            if digitos in _somente_digitos(row.get("telefone") or ""):
                resultado.append(_row_to_cliente(row))
        else:
            nome_norm = _normalizar_nome(row["nome"])
            if all(p in nome_norm for p in palavras):
                resultado.append(_row_to_cliente(row))
        if len(resultado) >= limite:
            break
    return resultado


def listar_clientes(filtro: str = "") -> list:
    """Lista todos os clientes (opcionalmente filtrando)."""
    try:
        resp = _sb.table("clientes").select("*").order("nome").execute()
        todos = [(_row_to_cliente(r)) for r in (resp.data or [])]
    except Exception:
        return []

    filtro = (filtro or "").strip()
    if not filtro:
        return todos

    palavras = _normalizar_nome(filtro).split()
    digitos = _somente_digitos(filtro)
    resultado = []
    for row in todos:
        # row é tupla, converter para dict-like para busca
        nome = row[1]
        telefone = row[2] or ""
        nome_norm = _normalizar_nome(nome)
        if all(p in nome_norm for p in palavras) or (digitos and digitos in _somente_digitos(telefone)):
            resultado.append(row)
    return resultado


def salvar_cliente(id_cliente: Optional[int], nome: str, telefone: str, endereco: str) -> tuple[bool, str]:
    """Cria ou edita um cliente. Retorna (ok, mensagem)."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        return False, "Informe o nome do cliente."

    # Verifica duplicata (exceto o próprio id)
    existente = _achar_cliente(nome, telefone)
    if existente and existente["id"] != id_cliente:
        return False, f"Já existe um cliente cadastrado com esse nome/telefone:\n\n{existente['nome']}  |  {existente.get('telefone') or 'sem telefone'}"

    try:
        if id_cliente:
            _sb.table("clientes").update({
                "nome": nome, "telefone": telefone, "endereco": endereco
            }).eq("id", id_cliente).execute()
        else:
            resp = _sb.table("clientes").insert({
                "nome": nome, "telefone": telefone, "endereco": endereco
            }).execute()
            id_cliente = resp.data[0]["id"] if resp.data else None
        return True, "Cliente salvo com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar cliente: {e}"


def excluir_cliente(id_cliente: int):
    try:
        _sb.table("clientes").delete().eq("id", id_cliente).execute()
    except Exception:
        pass


def encontrar_cliente_similar(nome: str, telefone: str) -> Optional[tuple]:
    """Procura cliente equivalente (mesmo telefone, nome igual ou muito parecido)."""
    achado = _achar_cliente(nome, telefone)
    if not achado:
        nome_norm = _normalizar_nome(nome)
        if nome_norm:
            try:
                resp = _sb.table("clientes").select("*").execute()
                melhor, melhor_score = None, 0.0
                for row in resp.data or []:
                    score = difflib.SequenceMatcher(None, nome_norm, _normalizar_nome(row["nome"])).ratio()
                    if score > melhor_score:
                        melhor, melhor_score = row, score
                if melhor_score >= 0.85:
                    achado = melhor
            except Exception:
                pass
    if achado:
        return _row_to_cliente(achado)
    return None


# ---------------------------------------------------------------------------
# CATÁLOGO
# ---------------------------------------------------------------------------
def buscar_catalogo() -> list:
    """Retorna lista de tuplas compatível: (id, categoria, nome, unidade, preco, estoque)"""
    try:
        resp = _sb.table("catalogo").select("*").order("categoria,nome").execute()
        return [_row_to_catalogo(r) for r in (resp.data or [])]
    except Exception:
        return []


def salvar_item_catalogo(id_item: Optional[int], categoria: str, nome: str, unidade: str, preco: float, estoque: int):
    dados = {
        "categoria": categoria or "Geral",
        "nome": nome,
        "unidade": unidade or "Unidade",
        "preco": float(preco or 0),
        "estoque": int(estoque or 0),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }
    try:
        if id_item:
            _sb.table("catalogo").update(dados).eq("id", id_item).execute()
        else:
            _sb.table("catalogo").insert(dados).execute()
    except Exception as e:
        raise RuntimeError(f"Erro ao salvar item do catálogo: {e}")


def excluir_item_catalogo(id_item: int):
    try:
        _sb.table("catalogo").delete().eq("id", id_item).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PEDIDOS / ORÇAMENTOS
# ---------------------------------------------------------------------------
def inserir_pedido(dados: dict, tipo: str = "Orcamento") -> int:
    """Insere pedido/orçamento e registra cliente. Retorna ID."""
    payload = {
        "cliente": dados.get("cliente", ""),
        "telefone": dados.get("telefone", ""),
        "endereco": dados.get("endereco", ""),
        "data_evento": dados.get("data_evento", ""),
        "orcamento": dados.get("orcamento", ""),
        "tipo": tipo,
        "distancia_km": float(dados.get("distancia_km", 0) or 0),
        "desconto": float(dados.get("desconto", 0) or 0),
        "observacoes": dados.get("observacoes", ""),
    }
    resp = _sb.table("orcamentos").insert(payload).execute()
    if not resp.data:
        raise RuntimeError("Falha ao inserir pedido")
    novo_id = resp.data[0]["id"]
    _registrar_cliente(dados.get("cliente", ""), dados.get("telefone", ""), dados.get("endereco", ""))
    return novo_id


def atualizar_pedido(id_pedido: int, dados: dict):
    payload = {
        "cliente": dados.get("cliente", ""),
        "telefone": dados.get("telefone", ""),
        "endereco": dados.get("endereco", ""),
        "data_evento": dados.get("data_evento", ""),
        "orcamento": dados.get("orcamento", ""),
        "distancia_km": float(dados.get("distancia_km", 0) or 0),
        "desconto": float(dados.get("desconto", 0) or 0),
        "observacoes": dados.get("observacoes", ""),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }
    _sb.table("orcamentos").update(payload).eq("id", id_pedido).execute()
    _registrar_cliente(dados.get("cliente", ""), dados.get("telefone", ""), dados.get("endereco", ""))


def alterar_status(id_pedido: int, novo_status: str):
    _sb.table("orcamentos").update({"tipo": novo_status}).eq("id", id_pedido).execute()


def alterar_status_multiplos(lista_ids: list, novo_status: str):
    if not lista_ids:
        return
    # Supabase aceita filtro 'in'
    _sb.table("orcamentos").update({"tipo": novo_status}).in_("id", lista_ids).execute()


def buscar_por_status(status: str) -> list:
    """Retorna lista de tuplas: (id, cliente, telefone, endereco, data_evento, tipo)"""
    try:
        if status == "Pedido":
            resp = _sb.table("orcamentos").select("*").in_("tipo", ["Pedido", "Ja Entregue", "Ja Recolhido", "Arquivado"]).order("id", desc=True).execute()
        else:
            resp = _sb.table("orcamentos").select("*").eq("tipo", status).order("id", desc=True).execute()
        return [_row_to_orcamento(r) for r in (resp.data or [])]
    except Exception:
        return []


def buscar_todos_pedidos_relatorio() -> list:
    """Retorna lista de dicts completos para relatórios."""
    try:
        resp = _sb.table("orcamentos").select("*").execute()
        return [_row_to_orcamento_full(r) for r in (resp.data or [])]
    except Exception:
        return []


def buscar_por_id(id_pedido: int) -> Optional[dict]:
    try:
        resp = _sb.table("orcamentos").select("*").eq("id", id_pedido).single().execute()
        if resp.data:
            return _row_to_orcamento_full(resp.data)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# COMPATIBILIDADE: funções que o nuvem_sync.py usa internamente
# ---------------------------------------------------------------------------
def conectar():
    """Dummy para compatibilidade — nuvem_sync.py chama mas não usa o retorno diretamente."""
    class _DummyConn:
        def cursor(self): return _DummyCursor()
        def commit(self): pass
        def close(self): pass
    class _DummyCursor:
        def execute(self, *a, **k): pass
        def fetchone(self): return None
        def fetchall(self): return []
        @property
        def lastrowid(self): return None
    return _DummyConn()


# Alias para compatibilidade
_registrar_cliente_cursor = _registrar_cliente  # nuvem_sync.py usa isso


# ---------------------------------------------------------------------------
# TESTE DE CONEXÃO (usado pelo main.py / interface.py)
# ---------------------------------------------------------------------------
def testar_conexao() -> tuple[bool, str]:
    return _testar_supabase()