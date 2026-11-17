#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de conexao Supabase e criacao das tabelas
Execute APOS configurar o .env com suas credenciais do Supabase
"""

from config_supabase import get_client, testar_conexao

print("=== TESTE DE CONEXAO SUPABASE ===\n")

ok, msg = testar_conexao()
print(f"Conexao: {'OK' if ok else 'FALHOU'} - {msg}")

if not ok:
    print("\nATENCAO: Configure o arquivo .env com suas credenciais do Supabase:")
    print("   1. Acesse https://supabase.com -> seu projeto -> Settings -> API")
    print("   2. Copie 'Project URL' para SUPABASE_URL")
    print("   3. Copie 'service_role' key (NAO anon key) para SUPABASE_KEY")
    print("   4. Edite o arquivo .env e salve")
    exit(1)

# Se conectou, testa as tabelas
sb = get_client()
print("\n=== VERIFICANDO TABELAS ===")

tabelas = ["catalogo", "clientes", "orcamentos"]
todas_ok = True
for t in tabelas:
    try:
        resp = sb.table(t).select("id", count="exact").limit(1).execute()
        print(f"  {t}: OK existe ({resp.count} registros)")
    except Exception as e:
        print(f"  {t}: ERRO - {e}")
        todas_ok = False

if not todas_ok:
    print("\nAVISO: Alguma tabela nao existe no Supabase.")
    print("   Execute o SQL do arquivo supabase_tabelas.sql no SQL Editor do Supabase.")

print("\n=== PROXIMOS PASSOS ===")
print("1. Se alguma tabela faltou, execute o SQL no Supabase SQL Editor")
print("2. Rode: python main.py")
print("3. Em outros PCs: clone a pasta, configure o mesmo .env, rode python main.py")