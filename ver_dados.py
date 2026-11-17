#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visualiza todos os dados do banco local (SQLite).
Use: python ver_dados.py
"""
import sqlite3
import os

BANCO = r"C:\Users\netho\OneDrive\Desktop\Modelo Renascer 1\banco_dados.db"

if not os.path.exists(BANCO):
    print(f"ERRO: Banco nao encontrado em {BANCO}")
    exit(1)

conn = sqlite3.connect(BANCO)
c = conn.cursor()

print("=" * 60)
print("          BASE DE DADOS LOCAL - MODELO RENASCER")
print("=" * 60)

# ----------------------------------------------------------
# 1. Catálogo
# ----------------------------------------------------------
print("\n--- CATÁLOGO DE PRODUTOS ---")
print(f"Total de itens: {c.execute('SELECT COUNT(*) FROM catalogo').fetchone()[0]}")
print("-" * 60)
# Cabeçalho
print(f"{'ID':>5} | {'Categoria':<20} | {'Nome':<30} | {'Unidade':<10} | {'Preço':>8} | {'Estoque':>8}")
print("-" * 60)
for row in c.execute("SELECT id, categoria, nome, unidade, preco, estoque_total FROM catalogo ORDER BY categoria, nome"):
    print(f"{row[0]:>5} | {row[1]:<20} | {row[2]:<30} | {row[3]:<10} | R$ {row[4]:>7} | {row[5]:>8}")
print("--- Fim do catálogo ---")

# ----------------------------------------------------------
# 2. Clientes
# ----------------------------------------------------------
print("\n--- CLIENTES ---")
print(f"Total de clientes: {c.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]}")
print("-" * 60)
print(f"{'ID':>5} | {'Nome':<30} | {'Telefone':<18} | {'Endereço':<30}")
print("-" * 60)
for row in c.execute("SELECT id, nome, telefone, endereco FROM clientes ORDER BY nome"):
    print(f"{row[0]:>5} | {row[1]:<30} | {row[2] or '':<18} | {row[3] or '':<30}")
print("--- Fim da lista de clientes ---")

# ----------------------------------------------------------
# 3. Pedidos / Orçamentos
# ----------------------------------------------------------
print("\n--- PEDIDOS / ORÇAMENTOS ---")
print(f"Total de pedidos: {c.execute('SELECT COUNT(*) FROM orcamentos').fetchone()[0]}")
print("-" * 70)
print(f"{'ID':>5} | {'Cliente':<20} | {'Tipo':<12} | {'Evento':<12} | {'Dist km':>7} | {'Desc':>6} | Status")
print("-" * 70)
for row in c.execute("SELECT id, cliente, tipo, data_evento, distancia_km, desconto, observacoes FROM orcamentos ORDER BY id DESC"):
    tipo = row[2] or "Orcamento"
    # Resumir status no base do tipo
    status = tipo
    print(f"{row[0]:>5} | {row[1] or '---':<20} | {status:<12} | {row[3] or '---':<12} | {row[4]:>7} | R$ {row[5]:>5} | {row[6] or '':<15}")
print("--- Fim da lista de pedidos ---")

conn.close()
print("\n" + "=" * 60)
print("Dados carregados com sucesso do banco LOCAL (SQLite).")
print("Nenhum dado foi perdido ou excluído.")
print("=" * 60)