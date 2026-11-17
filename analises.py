# -*- coding: utf-8 -*-
"""Motor de análises financeiras da Renascer Locações.

Funções puras (sem interface gráfica) que calculam, de forma dinâmica e
direto a partir dos pedidos e do catálogo:

  - Agregados de orçamentos/pedidos por SEMANA, MÊS e ANO
  - Ranking dos itens (ou categorias de materiais) mais locados,
    com quantidade e valor total
  - Perdas por semana: pedidos da semana de referência que não foram
    efetivados (permaneceram como orçamento ou foram cancelados)
  - Projeção futura de receita por semanas, meses e anos vindouros
"""

import re
import difflib
from datetime import datetime, timedelta

MESES_NOMES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def parse_data(data_str):
    """Converte datas em formato DD/MM/AAAA (ou ISO) em datetime."""
    if not data_str:
        return datetime.min
    data_str = str(data_str).strip()
    match_br = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', data_str)
    if match_br:
        d, m, y = int(match_br.group(1)), int(match_br.group(2)), int(match_br.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime(y, m, d)
        except ValueError:
            pass
    match_iso = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', data_str)
    if match_iso:
        y, m, d = int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            pass
    return datetime.min


def buscar_preco_catalogo(texto_item, catalogo):
    """Busca o preço unitário de um item no catálogo (matching tolerante)."""
    if not catalogo:
        return None, None

    itens_cat = []
    for c in catalogo:
        nome_orig = c[2]
        nome_norm = re.sub(r'[^\w\s]', ' ', nome_orig.lower())
        itens_cat.append({'orig': nome_orig, 'norm': nome_norm, 'preco': float(c[4])})

    texto_limpo = re.sub(r'R\$\s*\d+([.,]\d+)?', '', texto_item, flags=re.IGNORECASE)
    texto_norm = re.sub(r'[^\w\s]', ' ', texto_limpo.lower()).strip()

    for item in itens_cat:
        if item['norm'] in texto_norm or texto_norm in item['norm']:
            return item['preco'], item['orig']

    sub_itens = re.split(r'[,/]|(?:\s+e\s+)|\s+ou\s+', texto_norm)
    sub_itens = [s.strip() for s in sub_itens if s.strip()]

    if len(sub_itens) > 1:
        preco_acumulado = 0.0
        encontrou_algum = False
        nomes_encontrados = []

        for sub in sub_itens:
            melhor_match = None
            maior_ratio = 0.0
            for item in itens_cat:
                ratio = difflib.SequenceMatcher(None, sub, item['norm']).ratio()
                if sub in item['norm'] or item['norm'] in sub:
                    ratio = max(ratio, 0.8)
                if ratio > maior_ratio and ratio >= 0.5:
                    maior_ratio = ratio
                    melhor_match = item
            if melhor_match:
                preco_acumulado += melhor_match['preco']
                encontrou_algum = True
                nomes_encontrados.append(melhor_match['orig'])

        if encontrou_algum:
            nome_sugerido = " + ".join(nomes_encontrados)
            return preco_acumulado, nome_sugerido

    nomes_norm = [i['norm'] for i in itens_cat]
    matches = difflib.get_close_matches(texto_norm, nomes_norm, n=1, cutoff=0.4)
    if matches:
        for item in itens_cat:
            if item['norm'] == matches[0]:
                return item['preco'], item['orig']

    return None, None


def _categoria_do_item(nome_catalogo, catalogo):
    """Retorna a categoria de um item do catálogo pelo nome."""
    for c in catalogo:
        if len(c) > 4 and str(c[2]).strip() == str(nome_catalogo or "").strip():
            return str(c[1] or "").strip()
    return ""


def moeda(valor):
    """Formata valor no padrão brasileiro (R$ X.XXX,XX)."""
    return f"R$ {valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')


def chave_semana(dt):
    """Retorna (ano_iso, semana_iso) de uma data."""
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def intervalo_semana(ano_iso, semana_iso):
    """Retorna (segunda, domingo) da semana ISO informada."""
    inicio = datetime.fromisocalendar(ano_iso, semana_iso, 1)
    return inicio, inicio + timedelta(days=6)


def rotulo_semana(ano_iso, semana_iso):
    inicio, fim = intervalo_semana(ano_iso, semana_iso)
    return f"Semana {semana_iso:02d}/{ano_iso} ({inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')})"


def rotulo_mes(ano, mes):
    return f"{MESES_NOMES[mes - 1].capitalize()} de {ano}"


# ---------------------------------------------------------------------------
# Extração de itens e valores de um pedido
# ---------------------------------------------------------------------------
def extrair_itens(pedido, catalogo):
    """Devolve a lista de itens de um pedido:
    [{'qtd', 'material', 'nome_catalogo', 'v_unit', 'v_total', 'categoria'}]"""
    texto_orc = pedido.get("orcamento", "") or ""
    linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
    itens = []
    for linha in linhas:
        match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
        qtd = int(match_qtd.group(1)) if match_qtd else 1
        mat = match_qtd.group(2) if match_qtd else linha
        v_unit, nome_cat = buscar_preco_catalogo(mat, catalogo)
        if v_unit is None:
            v_unit = 0.0
        itens.append({
            "qtd": qtd,
            "material": mat,
            "nome_catalogo": nome_cat or mat,
            "v_unit": v_unit,
            "v_total": v_unit * qtd,
            "categoria": _categoria_do_item(nome_cat, catalogo) if nome_cat else "",
        })
    return itens


def valores_pedido(pedido, catalogo):
    """Calcula subtotal, frete, desconto, bruto e líquido de um pedido."""
    itens = extrair_itens(pedido, catalogo)
    subtotal = sum(i["v_total"] for i in itens)
    try:
        dist_km = float(pedido.get("distancia_km", 0.0) or 0.0)
    except (ValueError, TypeError):
        dist_km = 0.0
    frete = (dist_km * 4.0) * 1.10
    try:
        desconto = float(pedido.get("desconto", 0.0) or 0.0)
    except (ValueError, TypeError):
        desconto = 0.0
    bruto = subtotal + frete
    liquido = max(0.0, bruto - desconto)
    return {
        "itens": itens, "subtotal": subtotal, "frete": frete,
        "desconto": desconto, "bruto": bruto, "liquido": liquido,
    }


# ---------------------------------------------------------------------------
# Filtro por período (Semanal / Diário / Mensal / Anual)
# ---------------------------------------------------------------------------
def filtrar_por_periodo(pedidos, tipo_filtro, valor_filtro):
    """Filtra a lista de pedidos conforme o tipo/valor informados na tela."""
    tipo_filtro = (tipo_filtro or "Todos").strip()
    valor_filtro = (valor_filtro or "").strip()

    resultado = []
    for ped in pedidos:
        dt = parse_data(ped.get("data_evento", ""))

        if tipo_filtro == "Semanal" and valor_filtro:
            dt_filtro = parse_data(valor_filtro)
            if dt == datetime.min or dt_filtro == datetime.min:
                continue
            if chave_semana(dt) != chave_semana(dt_filtro):
                continue
        elif tipo_filtro == "Diário" and valor_filtro:
            dt_filtro = parse_data(valor_filtro)
            if dt == datetime.min or dt_filtro == datetime.min:
                continue
            if dt.date() != dt_filtro.date():
                continue
        elif tipo_filtro == "Mensal" and valor_filtro:
            partes = valor_filtro.split('/')
            if len(partes) == 2 and all(p.isdigit() for p in partes):
                mes, ano = int(partes[0]), int(partes[1])
                if dt == datetime.min or dt.month != mes or dt.year != ano:
                    continue
            elif dt == datetime.min or valor_filtro not in str(ped.get("data_evento", "")):
                continue
        elif tipo_filtro == "Anual" and valor_filtro:
            if dt == datetime.min:
                continue
            if str(dt.year) != valor_filtro and valor_filtro not in str(ped.get("data_evento", "")):
                continue

        resultado.append(ped)
    return resultado


# ---------------------------------------------------------------------------
# Agregados por período (semana / mês / ano)
# ---------------------------------------------------------------------------
def agregar_por_periodo(pedidos, catalogo, periodo):
    """periodo: 'semana' | 'mes' | 'ano'.
    Retorna lista ordenada de agregados com pedidos, itens, bruto,
    descontos, líquido e ticket médio."""
    grupos = {}
    for ped in pedidos:
        if ped.get("tipo") == "Cancelado":
            continue
        dt = parse_data(ped.get("data_evento", ""))
        if dt == datetime.min:
            continue

        if periodo == "semana":
            chave = chave_semana(dt)
        elif periodo == "mes":
            chave = (dt.year, dt.month)
        else:
            chave = (dt.year,)

        g = grupos.setdefault(chave, {
            "qtd_pedidos": 0, "itens": 0, "bruto": 0.0,
            "descontos": 0.0, "liquido": 0.0,
        })
        v = valores_pedido(ped, catalogo)
        g["qtd_pedidos"] += 1
        g["itens"] += sum(i["qtd"] for i in v["itens"])
        g["bruto"] += v["bruto"]
        g["descontos"] += v["desconto"]
        g["liquido"] += v["liquido"]

    saida = []
    for chave, g in sorted(grupos.items()):
        if periodo == "semana":
            rotulo = rotulo_semana(chave[0], chave[1])
        elif periodo == "mes":
            rotulo = rotulo_mes(chave[0], chave[1])
        else:
            rotulo = str(chave[0])
        ticket = (g["liquido"] / g["qtd_pedidos"]) if g["qtd_pedidos"] else 0.0
        saida.append({
            "rotulo": rotulo,
            "qtd_pedidos": g["qtd_pedidos"],
            "itens": g["itens"],
            "bruto": g["bruto"],
            "descontos": g["descontos"],
            "liquido": g["liquido"],
            "ticket": ticket,
        })
    return saida


# ---------------------------------------------------------------------------
# Ranking dos itens (ou categorias) mais locados
# ---------------------------------------------------------------------------
def ranking_itens(pedidos, catalogo, agrupar_por="item", somente_confirmados=True):
    """Devolve (ranking, valor_total, qtd_total).

    ranking: lista de {'nome', 'categoria', 'qtd', 'valor', 'percentual'}
    ordenada por quantidade (e valor) decrescentes.
    """
    cont = {}
    total_qtd = 0

    for ped in pedidos:
        if somente_confirmados and ped.get("tipo") in ("Orcamento", "Cancelado"):
            continue
        for it in extrair_itens(ped, catalogo):
            if agrupar_por == "item":
                chave = it["nome_catalogo"]
                categoria = it["categoria"]
            else:
                chave = it["categoria"] or "Sem categoria"
                categoria = ""
            row = cont.setdefault(chave, {
                "nome": chave, "categoria": categoria, "qtd": 0, "valor": 0.0,
            })
            row["qtd"] += it["qtd"]
            row["valor"] += it["v_total"]
            total_qtd += it["qtd"]

    ranking = sorted(cont.values(), key=lambda r: (-r["qtd"], -r["valor"]))
    total_valor = sum(r["valor"] for r in ranking)
    for r in ranking:
        r["percentual"] = (r["valor"] / total_valor * 100.0) if total_valor > 0 else 0.0
    return ranking, total_valor, total_qtd


# ---------------------------------------------------------------------------
# Perdas por semana (pedidos não efetivados)
# ---------------------------------------------------------------------------
def perdas_semana(pedidos, catalogo, data_referencia):
    """Analisa a semana que contém data_referencia.

    Considera como PERDA os pedidos cuja data do evento cai na semana e que
    não foram efetivados (status 'Orcamento' — não convertido — ou 'Cancelado').
    """
    dt_ref = parse_data(data_referencia)
    if dt_ref == datetime.min:
        return None

    chave = chave_semana(dt_ref)
    perdidos = []
    efetivados = []

    for ped in pedidos:
        dt = parse_data(ped.get("data_evento", ""))
        if dt == datetime.min or chave_semana(dt) != chave:
            continue
        v = valores_pedido(ped, catalogo)
        registro = {
            "id": ped.get("id"),
            "cliente": ped.get("cliente", ""),
            "telefone": ped.get("telefone", ""),
            "data_evento": ped.get("data_evento", ""),
            "tipo": ped.get("tipo", ""),
            "qtd_itens": sum(i["qtd"] for i in v["itens"]),
            "bruto": v["bruto"],
            "desconto": v["desconto"],
            "liquido": v["liquido"],
        }
        if ped.get("tipo") in ("Orcamento", "Cancelado"):
            registro["situacao"] = (
                "Cancelado" if ped.get("tipo") == "Cancelado"
                else "Orçamento não convertido"
            )
            perdidos.append(registro)
        else:
            efetivados.append(registro)

    perdidos.sort(key=lambda r: parse_data(r["data_evento"]))
    efetivados.sort(key=lambda r: parse_data(r["data_evento"]))

    qtd_perdidos = len(perdidos)
    qtd_efetivados = len(efetivados)
    total = qtd_perdidos + qtd_efetivados

    return {
        "semana": rotulo_semana(chave[0], chave[1]),
        "perdidos": perdidos,
        "efetivados": efetivados,
        "qtd_perdidos": qtd_perdidos,
        "qtd_efetivados": qtd_efetivados,
        "valor_perdido": sum(p["bruto"] for p in perdidos),
        "valor_efetivado": sum(p["liquido"] for p in efetivados),
        "taxa_perda": (qtd_perdidos / total * 100.0) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# Projeção futura (semanas / meses / anos)
# ---------------------------------------------------------------------------
def projecao_futura(pedidos, catalogo):
    """Projeção dinâmica baseada na média de movimento recente:
      - semanas: média das últimas 8 semanas com movimento -> próximas 8 semanas
      - meses:   média dos últimos 12 meses com movimento  -> próximos 12 meses
      - anos:    média dos últimos 5 anos com movimento    -> próximos 5 anos
    """
    pares = []  # (data_evento, receita_liquida)
    for ped in pedidos:
        if ped.get("tipo") == "Cancelado":
            continue
        dt = parse_data(ped.get("data_evento", ""))
        if dt == datetime.min:
            continue
        v = valores_pedido(ped, catalogo)
        pares.append((dt, v["liquido"]))

    total_receita = sum(v for _, v in pares)

    # ---------------- Semanais ----------------
    semanas = {}
    for dt, valor in pares:
        ch = chave_semana(dt)
        s = semanas.setdefault(ch, {"receita": 0.0, "pedidos": 0})
        s["receita"] += valor
        s["pedidos"] += 1
    semanas_ord = sorted(semanas.items(), key=lambda kv: kv[0])
    base_semanas = semanas_ord[-8:]
    if base_semanas:
        media_semana_rec = sum(s["receita"] for _, s in base_semanas) / len(base_semanas)
        media_semana_ped = sum(s["pedidos"] for _, s in base_semanas) / len(base_semanas)
        ultima_inicio = intervalo_semana(base_semanas[-1][0][0], base_semanas[-1][0][1])[0]
    else:
        media_semana_rec = 0.0
        media_semana_ped = 0.0
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ultima_inicio = hoje - timedelta(days=hoje.weekday())

    proxima_inicio = (ultima_inicio + timedelta(days=7))
    proxima_inicio = proxima_inicio - timedelta(days=proxima_inicio.weekday())

    proj_semanas = []
    for i in range(8):
        ini = proxima_inicio + timedelta(days=7 * i)
        iso = ini.isocalendar()
        proj_semanas.append({
            "periodo": rotulo_semana(iso[0], iso[1]),
            "pedidos": media_semana_ped,
            "receita": media_semana_rec,
            "ticket": (media_semana_rec / media_semana_ped) if media_semana_ped > 0 else 0.0,
        })

    # ---------------- Mensais ----------------
    meses = {}
    for dt, valor in pares:
        ch = (dt.year, dt.month)
        m = meses.setdefault(ch, {"receita": 0.0, "pedidos": 0})
        m["receita"] += valor
        m["pedidos"] += 1
    meses_ord = sorted(meses.items(), key=lambda kv: kv[0])
    base_meses = meses_ord[-12:]
    if base_meses:
        media_mes_rec = sum(m["receita"] for _, m in base_meses) / len(base_meses)
        media_mes_ped = sum(m["pedidos"] for _, m in base_meses) / len(base_meses)
        ultimo_ano, ultimo_mes = base_meses[-1][0]
    else:
        media_mes_rec = 0.0
        media_mes_ped = 0.0
        agora = datetime.now()
        ultimo_ano, ultimo_mes = agora.year, agora.month

    proj_meses = []
    for i in range(1, 13):
        m_total = ultimo_mes + i
        ano = ultimo_ano + (m_total - 1) // 12
        mes = (m_total - 1) % 12 + 1
        proj_meses.append({
            "periodo": rotulo_mes(ano, mes),
            "pedidos": media_mes_ped,
            "receita": media_mes_rec,
            "ticket": (media_mes_rec / media_mes_ped) if media_mes_ped > 0 else 0.0,
        })

    # ---------------- Anuais ----------------
    anos = {}
    for dt, valor in pares:
        ch = dt.year
        a = anos.setdefault(ch, {"receita": 0.0, "pedidos": 0})
        a["receita"] += valor
        a["pedidos"] += 1
    anos_ord = sorted(anos.items(), key=lambda kv: kv[0])
    base_anos = anos_ord[-5:]
    if base_anos:
        media_ano_rec = sum(a["receita"] for _, a in base_anos) / len(base_anos)
        media_ano_ped = sum(a["pedidos"] for _, a in base_anos) / len(base_anos)
        ultimo_ano = anos_ord[-1][0]
    else:
        media_ano_rec = 0.0
        media_ano_ped = 0.0
        ultimo_ano = datetime.now().year

    proj_anos = []
    for i in range(1, 6):
        ano = ultimo_ano + i
        proj_anos.append({
            "periodo": str(ano),
            "pedidos": media_ano_ped,
            "receita": media_ano_rec,
            "ticket": (media_ano_rec / media_ano_ped) if media_ano_ped > 0 else 0.0,
        })

    return {
        "total_receita": total_receita,
        "qtd_pedidos": len(pares),
        "base_semanas": len(base_semanas),
        "base_meses": len(base_meses),
        "base_anos": len(base_anos),
        "media_semana_rec": media_semana_rec,
        "media_semana_ped": media_semana_ped,
        "media_mes_rec": media_mes_rec,
        "media_mes_ped": media_mes_ped,
        "media_ano_rec": media_ano_rec,
        "media_ano_ped": media_ano_ped,
        "semanas": proj_semanas,
        "meses": proj_meses,
        "anos": proj_anos,
    }
