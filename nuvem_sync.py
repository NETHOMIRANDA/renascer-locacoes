"""
Módulo de Sincronização em Nuvem (Renascer Locações)
Conecta o sistema Desktop Python ao Aplicativo Web/Celular via Google Apps Script.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import database

ARQUIVO_CONFIG = "config_nuvem.json"
URL_PADRAO = "https://script.google.com/macros/s/AKfycybQoiNmyqc4DwM04p_sdVC50bJj3whQ_YQHm1clUipyvsIAVpYVY4X-pRijfWAQ981g/exec"
SENHA_PADRAO = "A103114"


def carregar_config():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"url": URL_PADRAO, "senha": SENHA_PADRAO, "auto_sync": True}


def salvar_config(url, senha, auto_sync=True):
    dados = {"url": url.strip(), "senha": senha.strip(), "auto_sync": auto_sync}
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    return dados


def _fazer_requisicao(payload=None, params=None):
    cfg = carregar_config()
    url = cfg.get("url", URL_PADRAO)
    senha = cfg.get("senha", SENHA_PADRAO)

    if not url or "/exec" not in url:
        return False, "URL da nuvem não configurada ou inválida."

    headers = {
        "User-Agent": "RenascerLocacoes-Desktop/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        if payload is not None:
            if "senha" not in payload:
                payload["senha"] = senha
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        else:
            if params is None:
                params = {}
            if "senha" not in params:
                params["senha"] = senha
            # Cache-buster: o Google cacheia respostas GET do Apps Script;
            # sem um parâmetro único o celular pode receber dados antigos.
            params["_t"] = str(time.time())
            query = urllib.parse.urlencode(params)
            req_url = f"{url}?{query}"
            req = urllib.request.Request(req_url, headers=headers, method="GET")

        with urllib.request.urlopen(req, timeout=20) as resp:
            conteudo = resp.read().decode("utf-8")
            try:
                return True, json.loads(conteudo)
            except Exception:
                return True, conteudo

    except urllib.error.HTTPError as e:
        return False, f"Erro HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Falha de conexão com a nuvem: {e.reason}"
    except Exception as e:
        return False, f"Erro na requisição: {str(e)}"


def testar_conexao():
    """Verifica se a URL da nuvem está acessível e respondendo."""
    ok, res = _fazer_requisicao(payload={"acao": "verificar"})
    if not ok:
        return False, res
    if isinstance(res, dict) and res.get("ok"):
        return True, "Conexão com a nuvem estabelecida com sucesso!"
    return False, "A nuvem respondeu, mas a senha de acesso está incorreta."


def puxar_pedidos_nuvem():
    """Busca novos pedidos feitos no celular/aplicativo e grava no banco de dados local."""
    ok, res = _fazer_requisicao()
    if not ok:
        return False, res, 0

    if not isinstance(res, dict) or "estado" not in res:
        return False, "Resposta da nuvem inválida.", 0

    estado = res.get("estado", {})
    pedidos_nuvem = estado.get("pedidos", [])
    if not pedidos_nuvem:
        return True, "Nenhum pedido pendente na nuvem.", 0

    conn = database.conectar()
    cursor = conn.cursor()

    novos_importados = 0

    for ped in pedidos_nuvem:
        cli_obj = ped.get("cliente")
        if isinstance(cli_obj, dict):
            cliente = str(cli_obj.get("nome") or "").strip()
            telefone = str(cli_obj.get("telefone") or "").strip()
            partes_end = [cli_obj.get("endereco"), cli_obj.get("bairro"), cli_obj.get("cidade"), cli_obj.get("cep")]
            endereco = ", ".join(p for p in partes_end if p and str(p).strip())
        else:
            cliente = str(cli_obj or ped.get("nome") or "").strip()
            telefone = str(ped.get("telefone") or "").strip()
            endereco = str(ped.get("endereco") or "").strip()

        if not cliente:
            continue

        data_evento = str(ped.get("dataEvento") or ped.get("data_evento") or ped.get("data") or "").strip()
        observacoes = str(ped.get("observacoes") or ped.get("obs") or ped.get("observacaoAdmin") or "").strip()
        distancia_km = float(ped.get("freteDistanciaKm") or ped.get("distancia_km") or ped.get("km") or 0.0)
        desconto = float(ped.get("desconto") or 0.0)

        itens_raw = ped.get("itens") or ped.get("orcamento") or []
        if isinstance(itens_raw, list):
            linhas_itens = []
            for item in itens_raw:
                if isinstance(item, dict):
                    qtd = item.get("qtd") or item.get("quantidade") or 1
                    nome_item = item.get("nome") or item.get("item") or ""
                    preco = item.get("preco") or item.get("valor") or ""
                    linhas_itens.append(f"{qtd}x {nome_item} (R$ {preco})".strip())
                else:
                    linhas_itens.append(str(item))
            texto_itens = "\n".join(linhas_itens)
        else:
            texto_itens = str(itens_raw).strip()

        # Evita duplicar o mesmo pedido se já existir para o mesmo cliente na mesma data
        cursor.execute(
            "SELECT id FROM orcamentos WHERE cliente = ? AND (data_evento = ? OR (data_evento IS NULL AND ? = '')) AND orcamento = ?",
            (cliente, data_evento, data_evento, texto_itens)
        )
        ja_existe = cursor.fetchone()

        if not ja_existe:
            status_tipo = 'Pedido' if ped.get("status") in ['aprovado', 'pago_enviado', 'Pedido'] else 'Orcamento'
            cursor.execute("""
                INSERT INTO orcamentos (cliente, telefone, endereco, data_evento, orcamento, tipo, distancia_km, desconto, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cliente, telefone, endereco, data_evento, texto_itens, status_tipo, distancia_km, desconto, observacoes))

            # Atualiza/Cadastra cliente
            database._registrar_cliente_cursor(cursor, cliente, telefone, endereco)
            novos_importados += 1

    conn.commit()
    conn.close()

    msg = f"{novos_importados} novos pedidos importados do celular com sucesso!" if novos_importados > 0 else "Tudo em dia! Nenhum pedido novo."
    return True, msg, novos_importados


def enviar_catalogo_nuvem():
    """Envia o catálogo de produtos e preços do computador para o aplicativo no celular."""
    itens_db = database.buscar_catalogo()
    if not itens_db:
        return False, "Catálogo local vazio."

    lista_itens_app = []
    # Marca de tempo obrigatória: a ponte só substitui um item existente
    # se o item enviado for MAIS RECENTE (campo "atualizadoEm").
    agora = datetime.now(timezone.utc).isoformat()
    for row in itens_db:
        # row: (id, categoria, nome, unidade, preco, estoque)
        lista_itens_app.append({
            "id": row[0],
            "categoria": row[1] or "Geral",
            "nome": row[2],
            "unidade": row[3] or "Unidade",
            "preco": float(row[4] or 0.0),
            "estoque": int(row[5] or 0),
            "atualizadoEm": agora
        })

    payload = {
        "acao": "salvar",
        "estado": {
            "itens": lista_itens_app
        }
    }

    ok, res = _fazer_requisicao(payload=payload)
    if not ok:
        return False, res

    return True, f"{len(lista_itens_app)} itens do catálogo enviados para o aplicativo dos clientes!"


def sincronizar_tudo():
    """Executa a sincronização completa (envia catálogo atualizado e baixa novos pedidos)."""
    sucesso_envio, msg_envio = enviar_catalogo_nuvem()
    sucesso_busca, msg_busca, qtd_novos = puxar_pedidos_nuvem()

    if not sucesso_envio and not sucesso_busca:
        return False, f"Falha na sincronização:\n- Envio: {msg_envio}\n- Busca: {msg_busca}", 0

    resumo = []
    if sucesso_envio:
        resumo.append(f"✅ {msg_envio}")
    else:
        resumo.append(f"⚠️ {msg_envio}")

    if sucesso_busca:
        resumo.append(f"✅ {msg_busca}")
    else:
        resumo.append(f"⚠️ {msg_busca}")

    return True, "\n".join(resumo), qtd_novos
