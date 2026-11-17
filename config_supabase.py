"""
Configuração do Supabase (PostgreSQL na nuvem)
Carrega variáveis de ambiente do .env e cria cliente Supabase.
"""

import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega .env da pasta do projeto
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service_role key (NÃO anon key)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL e SUPABASE_KEY devem estar definidos no arquivo .env\n"
        "Copie .env.example para .env e preencha com suas credenciais do Supabase."
    )

# Cliente Supabase (usa service_role para acesso total ao banco)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_client() -> Client:
    """Retorna o cliente Supabase configurado."""
    return supabase


def testar_conexao() -> tuple[bool, str]:
    """Testa se consegue conectar ao Supabase."""
    try:
        # Tenta uma query simples
        supabase.table("catalogo").select("id", count="exact").limit(1).execute()
        return True, "Conexão com Supabase estabelecida com sucesso!"
    except Exception as e:
        return False, f"Falha na conexão com Supabase: {e}"