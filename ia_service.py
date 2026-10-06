import os
import json
import re

try:
    import google.generativeai as genai
except ImportError:
    genai = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def analisar_texto(texto_usuario):
    if not texto_usuario or not texto_usuario.strip():
        return None

    if not genai or not GEMINI_API_KEY:
        return _parser_heuristico_local(texto_usuario)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Você é um assistente da empresa Renascer Locações.
        Sua tarefa é analisar o texto de um pedido/orçamento recebido por mensagem ou WhatsApp e extrair as seguintes informações em formato JSON estrito:

        Campos obrigatórios no JSON:
        - "cliente": Nome do cliente (string). Se não encontrar, retorne "".
        - "telefone": Número de telefone ou WhatsApp (string). Se não encontrar, retorne "".
        - "endereco": Endereço completo de entrega (string). Se não encontrar, retorne "".
        - "data_evento": Data do evento ou entrega (string). Se não encontrar, retorne "".
        - "distancia_km": Distância em KM caso informada (número). Se não encontrar, retorne 0.
        - "orcamento": Lista de itens solicitados no formato "QTD NOME_DO_ITEM" (uma linha por item, string única com separadores de quebra de linha \\n).

        Texto para análise:
        \"\"\"{texto_usuario}\"\"\"
        """

        resposta = model.generate_content(prompt)
        texto_resposta = resposta.text.strip()

        texto_resposta = re.sub(r'^```json\s*', '', texto_resposta, flags=re.MULTILINE)
        texto_resposta = re.sub(r'^```\s*', '', texto_resposta, flags=re.MULTILINE)
        texto_resposta = re.sub(r'```$', '', texto_resposta, flags=re.MULTILINE).strip()

        dados = json.loads(texto_resposta)

        resultado = {
            "cliente": str(dados.get("cliente", "")).strip(),
            "telefone": str(dados.get("telefone", "")).strip(),
            "endereco": str(dados.get("endereco", "")).strip(),
            "data_evento": str(dados.get("data_evento", "")).strip(),
            "distancia_km": float(dados.get("distancia_km", 0.0) or 0.0),
            "orcamento": str(dados.get("orcamento", "")).strip()
        }

        return resultado

    except Exception:
        return _parser_heuristico_local(texto_usuario)


def _parser_heuristico_local(texto):
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]

    cliente = ""
    telefone = ""
    endereco = ""
    data_evento = ""
    distancia_km = 0.0
    itens = []

    km_match = re.search(r'(\d+(?:[.,]\d+)?)\s*km', texto, re.IGNORECASE)
    if km_match:
        try:
            distancia_km = float(km_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    for linha in linhas:
        tel_match = re.search(r'(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-\s]?\d{4}', linha)
        if tel_match and not telefone:
            telefone = tel_match.group(0)

        data_match = re.search(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', linha)
        if data_match and not data_evento:
            data_evento = data_match.group(0)

        if re.search(r'\b(cliente|nome)\b\s*[:\-=]', linha, re.IGNORECASE) and not cliente:
            cliente = re.sub(r'\b(cliente|nome)\b\s*[:\-=]', '', linha, flags=re.IGNORECASE).strip()

        elif re.search(r'\b(endereço|endereco|rua|av|avenida|bairro|quadra|lote)\b', linha, re.IGNORECASE) and not endereco:
            endereco = re.sub(r'\b(endereço|endereco)\b\s*[:\-=]?', '', linha, flags=re.IGNORECASE).strip()

        elif re.match(r'^\d+\s*(?:x|un|jogos|jogo)?\s+', linha, re.IGNORECASE):
            itens.append(linha)
        elif not cliente and not any(kw in linha.lower() for kw in ['rua', 'av', 'tel', 'data', 'entrega', 'orçamento', 'km']):
            if len(linha.split()) <= 4 and not re.search(r'\d', linha):
                cliente = linha

    return {
        "cliente": cliente,
        "telefone": telefone,
        "endereco": endereco,
        "data_evento": data_evento,
        "distancia_km": distancia_km,
        "orcamento": "\n".join(itens) if itens else texto
    }
