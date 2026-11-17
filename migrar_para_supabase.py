#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRAÇÃO SQLite -> Supabase
Move TODOS os dados do banco local (banco_dados.db) para o Supabase
preservando IDs, clientes, pedidos e catálogo.
Execute UMA VEZ após configurar .env e criar tabelas no Supabase.
"""

import sqlite3
import os
from datetime import datetime, timezone
from config_supabase import get_client, testar_conexao

print("=== MIGRAÇÃO SQLITE -> SUPABASE ===\n")

# 1. Testa conexão Supabase
ok, msg = testar_conexao()
if not ok:
    print(f"ERRO: {msg}")
    print("Configure .env e crie tabelas no Supabase primeiro.")
    exit(1)

sb = get_client()
print("Conexao Supabase: OK")

# 2. Conecta SQLite local
sqlite_path = "banco_dados.db"
if not os.path.exists(sqlite_path):
    print(f"ERRO: {sqlite_path} nao encontrado")
    exit(1)

conn = sqlite3.connect(sqlite_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"\nBanco local: {sqlite_path}")
cur.execute("SELECT COUNT(*) FROM clientes"); print(f"  Clientes: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM orcamentos"); print(f"  Pedidos/Orcamentos: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM catalogo"); print(f"  Catalogo: {cur.fetchone()[0]}")

input("\nPressione ENTER para iniciar a migracao (ou Ctrl+C para cancelar)...")

# ------------------------------------------------------------
# MIGRAR CATÁLOGO
# ------------------------------------------------------------
print("\n--- Migrando CATALOGO ---")
cur.execute("SELECT id, categoria, nome, unidade, preco, estoque_total FROM catalogo ORDER BY id")
catalogo_rows = cur.fetchall()

migrados_cat = 0
for row in catalogo_rows:
    try:
        # Tenta inserir com ID específico (upsert)
        dados = {
            "id": row["id"],
            "categoria": row["categoria"] or "Geral",
            "nome": row["nome"],
            "unidade": row["unidade"] or "Unidade",
            "preco": float(row["preco"] or 0),
            "estoque": int(row["estoque_total"] or 0),
            "ativo": True,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }
        sb.table("catalogo").upsert(dados, on_conflict="id").execute()
        migrados_cat += 1
    except Exception as e:
        print(f"  ERRO item {row['id']} ({row['nome']}): {e}")

print(f"  Catalogo: {migrados_cat}/{len(catalogo_rows)} migrados")

# ------------------------------------------------------------
# MIGRAR CLIENTES
# ------------------------------------------------------------
print("\n--- Migrando CLIENTES ---")
cur.execute("SELECT id, nome, telefone, endereco FROM clientes ORDER BY id")
clientes_rows = cur.fetchall()

migrados_cli = 0
for row in clientes_rows:
    try:
        dados = {
            "id": row["id"],
            "nome": row["nome"],
            "telefone": row["telefone"],
            "endereco": row["endereco"],
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        sb.table("clientes").upsert(dados, on_conflict="id").execute()
        migrados_cli += 1
    except Exception as e:
        print(f"  ERRO cliente {row['id']} ({row['nome']}): {e}")

print(f"  Clientes: {migrados_cli}/{len(clientes_rows)} migrados")

# ------------------------------------------------------------
# MIGRAR PEDIDOS/ORÇAMENTOS
# ------------------------------------------------------------
print("\n--- Migrando PEDIDOS/ORCAMENTOS ---")
cur.execute("""
    SELECT id, cliente, telefone, endereco, data_evento, orcamento, 
           tipo, distancia_km, desconto, observacoes
    FROM orcamentos ORDER BY id
""")
orcamentos_rows = cur.fetchall()

migrados_ped = 0
for row in orcamentos_rows:
    try:
        dados = {
            "id": row["id"],
            "cliente": row["cliente"],
            "telefone": row["telefone"],
            "endereco": row["endereco"],
            "data_evento": row["data_evento"],
            "orcamento": row["orcamento"],
            "tipo": row["tipo"] or "Orcamento",
            "distancia_km": float(row["distancia_km"] or 0),
            "desconto": float(row["desconto"] or 0),
            "observacoes": row["observacoes"],
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }
        sb.table("orcamentos").upsert(dados, on_conflict="id").execute()
        migrados_ped += 1
    except Exception as e:
        print(f"  ERRO pedido {row['id']}: {e}")

print(f"  Pedidos: {migrados_ped}/{len(orcamentos_rows)} migrados")

# ------------------------------------------------------------
# VERIFICAÇÃO FINAL
# ------------------------------------------------------------
print("\n=== VERIFICACAO FINAL NO SUPABASE ===")
for t in ["catalogo", "clientes", "orcamentos"]:
    try:
        resp = sb.table(t).select("id", count="exact").execute()
        print(f"  {t}: {resp.count} registros")
    except Exception as e:
        print(f"  {t}: ERRO - {e}")

conn.close()
print("\n=== MIGRACAO CONCLUIDA ===")
print("Agora rode: python main.py")
print("Todos os PCs que usarem o mesmo .env verao os mesmos dados em tempo real.")