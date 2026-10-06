import os
import re
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Diretório padrão de saída: pasta 'PDF' na raiz do projeto
DIRETORIO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDF")

def _obter_caminho_final(caminho_saida):
    """Garante que a pasta de destino exista e evita sobrescrever arquivos."""
    os.makedirs(DIRETORIO_SAIDA, exist_ok=True)
    nome_base, ext = os.path.splitext(os.path.basename(caminho_saida))
    caminho_completo = os.path.join(DIRETORIO_SAIDA, f"{nome_base}{ext}")
    
    contador = 1
    while os.path.exists(caminho_completo):
        caminho_completo = os.path.join(DIRETORIO_SAIDA, f"{nome_base}_{contador}{ext}")
        contador += 1
        
    return caminho_completo


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 10)
        self.setFillColor(colors.HexColor("#000000"))
        self.setStrokeColor(colors.HexColor("#999999"))
        self.setLineWidth(0.8)
        
        largura_pagina = self._pagesize[0]
        self.line(54, 36, largura_pagina - 54, 36)
        
        text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(largura_pagina - 54, 20, text)
        self.drawString(54, 20, "Renascer Locações - Gestão de Entregas")
        self.restoreState()


def _buscar_preco_catalogo_local(texto_item, catalogo):
    if not catalogo or not texto_item:
        return None, None
    texto_norm = re.sub(r'[^\w\s]', ' ', str(texto_item).lower()).strip()
    for c in catalogo:
        if len(c) > 4:
            nome_orig = str(c[2])
            nome_norm = re.sub(r'[^\w\s]', ' ', nome_orig.lower()).strip()
            if nome_norm in texto_norm or texto_norm in nome_norm:
                try:
                    return float(c[4]), nome_orig
                except (ValueError, TypeError):
                    pass
    return None, None


# =========================================================
# RELATÓRIO DE ENTREGAS (ALTA VISIBILIDADE / FONTE GRANDE)
# =========================================================
def gerar_relatorio_entregas(lista_pedidos, caminho_saida=None):
    """Gera o PDF do Relatório de Entregas otimizado para alta legibilidade."""
    if not caminho_saida:
        data_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        caminho_saida = f"relatorio_entregas_{data_str}.pdf"

    caminho_final = _obter_caminho_final(caminho_saida)
    doc = SimpleDocTemplate(caminho_final, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)
    story = []
    styles = getSampleStyleSheet()

    # Fontes e tamanhos aumentados para facilitar leitura visual
    title_style = ParagraphStyle('TitleRel', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor("#000000"), spaceAfter=3)
    sub_title = ParagraphStyle('SubRel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#333333"), spaceAfter=14)
    
    val_style = ParagraphStyle('ValStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=15, textColor=colors.HexColor("#000000"), spaceAfter=4)
    item_style = ParagraphStyle('ItemStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, textColor=colors.HexColor("#000000"), spaceAfter=4)
    status_header_style = ParagraphStyle('StatusHeadStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#000000"), alignment=1)

    story.append(Paragraph("<b>RENASCER LOCAÇÕES - RELATÓRIO DE ENTREGAS</b>", title_style))
    story.append(Paragraph(f"Emitido em: {datetime.now().strftime('%d/%m/%Y às %H:%M')} | Total de Entregas: {len(lista_pedidos)}", sub_title))

    for ped in lista_pedidos:
        # --- LADO ESQUERDO: Dados do Cliente e Evento ---
        dados_cliente_html = f"""
        <font size=12><b>ID Pedido: #{ped.get('id', '')}</b></font><br/>
        <b>Cliente:</b> {ped.get('cliente', '')}<br/>
        <b>Telefone:</b> {ped.get('telefone', '')}<br/>
        <b>Data do Evento:</b> {ped.get('data_evento', '')}<br/>
        <b>Status:</b> {ped.get('status', 'Pendente')}<br/>
        <b>Endereço:</b> {ped.get('endereco', '')}
        """
        if ped.get("observacoes"):
            dados_cliente_html += f"<br/><b>Obs:</b> {ped.get('observacoes')}"

        col_esquerda = Paragraph(dados_cliente_html, val_style)

        # --- LADO DIREITO: Marcações Expressivas + Lista de Materiais ---
        # Tabela de Status Expressivos (Maior e com bordas fortes)
        t_status = Table([
            [
                Paragraph("<b>[ &nbsp; ] ENTREGUE</b>", status_header_style),
                Paragraph("<b>[ &nbsp; ] RECOLHIDO</b>", status_header_style),
                Paragraph("<b>[ &nbsp; ] PAGO</b>", status_header_style)
            ]
        ], colWidths=[90, 95, 80])
        
        t_status.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#D4EFDF")),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#FCF3CF")),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#D6EAF8")),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#000000")),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor("#000000")),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        # Construção dos materiais com caixa de seleção individual bem visível
        texto_orc = ped.get("orcamento", "") or ""
        linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
        
        materiais_html = "<b>CONFERÊNCIA DE MATERIAIS:</b><br/><br/>"
        if linhas:
            for l in linhas:
                match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', l, re.IGNORECASE)
                if match_qtd:
                    qtd = match_qtd.group(1)
                    mat = match_qtd.group(2)
                    materiais_html += f"<b>[ &nbsp; ] &nbsp; {qtd}</b> {mat}<br/>"
                else:
                    materiais_html += f"<b>[ &nbsp; ] &nbsp;</b> {l}<br/>"
        else:
            materiais_html += "<i>Nenhum material discriminado.</i>"

        col_direita_content = [
            t_status,
            Spacer(1, 8),
            Paragraph(materiais_html, item_style)
        ]

        # Montagem do Card do Pedido com alta visibilidade
        t_card = Table([[col_esquerda, col_direita_content]], colWidths=[260, 280])
        t_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#333333")),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor("#777777")),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(KeepTogether([t_card, Spacer(1, 10)]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return caminho_final


# ==========================================
# ORÇAMENTO / PEDIDO INDIVIDUAL (DOCUMENTO PROFISSIONAL)
# ==========================================
VALIDADE_ORCAMENTO_DIAS = 7

COR_MARINHO = "#0F172A"
COR_TEXTO = "#1E293B"
COR_MUTED = "#64748B"
COR_LINHA = "#E2E8F0"
COR_FUNDO_SUAVE = "#F8FAFC"


def _moeda(valor):
    return f"R$ {valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')


def _esc(texto):
    """Escapa texto digitado pelo usuário para uso seguro em Paragraph."""
    return xml_escape(str(texto or "")).replace("\n", "<br/>")


def _tipo_documento(tipo):
    """Define o nome e a identidade visual do documento conforme onde ele se encontra:
    Controle de Orçamentos -> ORÇAMENTO | Gestão de Entrega -> PEDIDO."""
    tipo = (tipo or "Orcamento").strip()
    if tipo == "Orcamento":
        return {"titulo": "ORÇAMENTO", "nome": "Orçamento", "prefixo": "orcamento",
                "cor": "#2563EB", "status": "AGUARDANDO APROVAÇÃO", "eh_orcamento": True}
    if tipo == "Cancelado":
        return {"titulo": "ORÇAMENTO", "nome": "Orçamento", "prefixo": "orcamento",
                "cor": "#DC2626", "status": "CANCELADO", "eh_orcamento": True}
    status = {"Pedido": "CONFIRMADO", "Ja Entregue": "ENTREGUE",
              "Ja Recolhido": "RECOLHIDO", "Arquivado": "ARQUIVADO"}.get(tipo, "CONFIRMADO")
    return {"titulo": "PEDIDO", "nome": "Pedido", "prefixo": "pedido",
            "cor": "#059669", "status": status, "eh_orcamento": False}


def _fabrica_canvas_documento(texto_rodape):
    """Canvas com rodapé profissional (identificação do documento + paginação)."""
    class DocumentoCanvas(NumberedCanvas):
        def draw_page_number(self, page_count):
            self.saveState()
            largura_pagina = self._pagesize[0]
            self.setStrokeColor(colors.HexColor(COR_LINHA))
            self.setLineWidth(0.8)
            self.line(40, 38, largura_pagina - 40, 38)
            self.setFillColor(colors.HexColor(COR_MUTED))
            self.setFont("Helvetica", 8)
            self.drawString(40, 25, texto_rodape)
            self.drawRightString(largura_pagina - 40, 25, f"Página {self._pageNumber} de {page_count}")
            self.restoreState()
    return DocumentoCanvas


def _parse_float(valor):
    try:
        return float(str(valor or 0.0).replace(',', '.'))
    except ValueError:
        return 0.0


def gerar_pdf_pedido(dados_pedido, catalogo=None, caminho_saida=None):
    """Gera o PDF de Orçamento ou de Pedido, conforme o status (tipo) do registro."""
    info_doc = _tipo_documento(dados_pedido.get('tipo'))
    cor_destaque = colors.HexColor(info_doc["cor"])
    id_ped = dados_pedido.get('id', '')
    numero = f"{int(id_ped):04d}" if str(id_ped).isdigit() else str(id_ped or "-")

    if not caminho_saida:
        cliente_clean = re.sub(r'[^\w\s-]', '', dados_pedido.get('cliente', 'cliente') or 'cliente').strip().replace(' ', '_')
        prefixo = info_doc["prefixo"]
        caminho_saida = f"{prefixo}_{id_ped}_{cliente_clean}.pdf" if id_ped else f"{prefixo}_{cliente_clean}.pdf"

    caminho_final = _obter_caminho_final(caminho_saida)
    margem = 40
    largura = A4[0] - 2 * margem  # ~515 pt
    doc = SimpleDocTemplate(caminho_final, pagesize=A4, leftMargin=margem, rightMargin=margem,
                            topMargin=34, bottomMargin=56,
                            title=f"{info_doc['nome']} Nº {numero} - Renascer Locações",
                            author="Renascer Locações e Eventos")
    styles = getSampleStyleSheet()

    # ---------- Estilos ----------
    st_marca = ParagraphStyle('Marca', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=22, leading=24, textColor=colors.white)
    st_marca_sub = ParagraphStyle('MarcaSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor("#94A3B8"))
    st_doc_titulo = ParagraphStyle('DocTitulo', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=22, leading=24, textColor=colors.white, alignment=2)
    st_doc_num = ParagraphStyle('DocNum', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=14, textColor=colors.HexColor("#CBD5E1"), alignment=2)
    st_secao = ParagraphStyle('Secao', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=cor_destaque, spaceBefore=14, spaceAfter=4)
    st_label = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=9, textColor=colors.HexColor(COR_MUTED))
    st_valor = ParagraphStyle('Valor', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=colors.HexColor(COR_TEXTO))
    st_cel = ParagraphStyle('Cel', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=12, textColor=colors.HexColor(COR_TEXTO))
    st_cel_c = ParagraphStyle('CelC', parent=st_cel, alignment=1)
    st_cel_r = ParagraphStyle('CelR', parent=st_cel, alignment=2)
    st_cel_muted = ParagraphStyle('CelM', parent=st_cel_r, textColor=colors.HexColor("#94A3B8"), fontName='Helvetica-Oblique', fontSize=8.5)
    st_cab = ParagraphStyle('Cab', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white)
    st_cab_c = ParagraphStyle('CabC', parent=st_cab, alignment=1)
    st_cab_r = ParagraphStyle('CabR', parent=st_cab, alignment=2)
    st_tot_l = ParagraphStyle('TotL', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=12, textColor=colors.HexColor(COR_MUTED))
    st_tot_r = ParagraphStyle('TotR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor(COR_TEXTO), alignment=2)
    st_total_l = ParagraphStyle('TotalL', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=colors.white)
    st_total_r = ParagraphStyle('TotalR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.white, alignment=2)
    st_obs = ParagraphStyle('Obs', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor(COR_TEXTO))
    st_termo = ParagraphStyle('Termo', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor(COR_MUTED), leftIndent=8, bulletIndent=0)
    st_ass = ParagraphStyle('Ass', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor(COR_MUTED), alignment=1)

    story = []
    agora = datetime.now()

    # ---------- Cabeçalho ----------
    chip_status = Table([[Paragraph(f"<font color='white'><b>{info_doc['status']}</b></font>",
                                    ParagraphStyle('Chip', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1))]],
                        colWidths=[150])
    chip_status.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), cor_destaque),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    largura_bloco_direito = largura * 0.5 - 36
    chip_alinhado = Table([["", chip_status]], colWidths=[largura_bloco_direito - 150, 150])
    chip_alinhado.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    bloco_direito = [
        Paragraph(info_doc["titulo"], st_doc_titulo),
        Paragraph(f"Nº {numero}", st_doc_num),
        Spacer(1, 4),
        chip_alinhado,
    ]

    t_head = Table([[
        [Paragraph("RENASCER", st_marca), Paragraph("LOCAÇÕES E EVENTOS", st_marca_sub)],
        bloco_direito,
    ]], colWidths=[largura * 0.5, largura * 0.5])
    t_head.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(COR_MARINHO)),
        ('LEFTPADDING', (0, 0), (-1, -1), 18), ('RIGHTPADDING', (0, 0), (-1, -1), 18),
        ('TOPPADDING', (0, 0), (-1, -1), 16), ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 4, cor_destaque),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 8))

    # Linha de datas
    partes_meta = [f"Emitido em <b>{agora.strftime('%d/%m/%Y')}</b> às {agora.strftime('%H:%M')}"]
    if info_doc["eh_orcamento"] and info_doc["status"] != "CANCELADO":
        validade = agora + timedelta(days=VALIDADE_ORCAMENTO_DIAS)
        partes_meta.append(f"Válido até <b>{validade.strftime('%d/%m/%Y')}</b>")
    story.append(Paragraph("&nbsp;&nbsp;|&nbsp;&nbsp;".join(partes_meta),
                           ParagraphStyle('Meta', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor(COR_MUTED))))

    # ---------- Dados do cliente ----------
    story.append(Paragraph("DADOS DO CLIENTE E DO EVENTO", st_secao))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor(COR_LINHA), spaceAfter=6))

    def campo(rotulo, valor):
        return [Paragraph(rotulo.upper(), st_label), Paragraph(_esc(valor) or "-", st_valor)]

    linhas_cliente = [
        [campo("Cliente", dados_pedido.get('cliente')), campo("Telefone", dados_pedido.get('telefone'))],
        [campo("Endereço de entrega", dados_pedido.get('endereco')), campo("Data do evento", dados_pedido.get('data_evento'))],
    ]
    if dados_pedido.get("cor_toalha"):
        linhas_cliente.append([campo("Cor da toalha", dados_pedido.get('cor_toalha')), ""])

    t_cliente = Table(linhas_cliente, colWidths=[largura * 0.6, largura * 0.4])
    t_cliente.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(COR_FUNDO_SUAVE)),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(COR_LINHA)),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor(COR_LINHA)),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE', (0, 0), (0, -1), 3, cor_destaque),
    ]))
    story.append(t_cliente)

    # ---------- Itens ----------
    story.append(Paragraph("ITENS DO " + info_doc["titulo"], st_secao))

    t_items_data = [[Paragraph("ITEM", st_cab_c), Paragraph("DESCRIÇÃO", st_cab), Paragraph("QTD", st_cab_c),
                     Paragraph("VALOR UNIT.", st_cab_r), Paragraph("TOTAL", st_cab_r)]]

    texto_orc = dados_pedido.get("orcamento", "") or ""
    linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
    subtotal_itens = 0.0

    for idx, linha in enumerate(linhas, start=1):
        match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
        qtd = int(match_qtd.group(1)) if match_qtd else 1
        mat = match_qtd.group(2) if match_qtd else linha

        v_unit, _ = _buscar_preco_catalogo_local(mat, catalogo)
        if v_unit is not None:
            v_tot = v_unit * qtd
            subtotal_itens += v_tot
            cel_unit, cel_tot = Paragraph(_moeda(v_unit), st_cel_r), Paragraph(f"<b>{_moeda(v_tot)}</b>", st_cel_r)
        else:
            cel_unit, cel_tot = Paragraph("a consultar", st_cel_muted), Paragraph("a consultar", st_cel_muted)

        t_items_data.append([Paragraph(f"{idx:02d}", st_cel_c), Paragraph(_esc(mat), st_cel),
                             Paragraph(str(qtd), st_cel_c), cel_unit, cel_tot])

    if len(t_items_data) == 1:
        t_items_data.append([Paragraph("-", st_cel_c), Paragraph("<i>Nenhum item discriminado.</i>", st_cel), "", "", ""])

    t_items = Table(t_items_data, colWidths=[38, largura - 38 - 44 - 90 - 90, 44, 90, 90], repeatRows=1)
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COR_MARINHO)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(COR_FUNDO_SUAVE)]),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor(COR_LINHA)),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(COR_LINHA)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 12))

    # ---------- Resumo financeiro + observações ----------
    dist_km = _parse_float(dados_pedido.get("distancia_km"))
    desconto = _parse_float(dados_pedido.get("desconto"))
    frete = (dist_km * 4.0) * 1.10
    total_geral = max(0.0, (subtotal_itens + frete) - desconto)

    linhas_tot = [
        [Paragraph("Subtotal dos itens", st_tot_l), Paragraph(_moeda(subtotal_itens), st_tot_r)],
        [Paragraph(f"Frete ({dist_km:.1f} km)", st_tot_l), Paragraph(_moeda(frete), st_tot_r)],
        [Paragraph("Desconto concedido", st_tot_l), Paragraph(f"- {_moeda(desconto)}", st_tot_r)],
        [Paragraph("TOTAL GERAL", st_total_l), Paragraph(_moeda(total_geral), st_total_r)],
    ]
    largura_tot = 230
    t_tot = Table(linhas_tot, colWidths=[110, largura_tot - 110])
    t_tot.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 2), colors.HexColor(COR_FUNDO_SUAVE)),
        ('BOX', (0, 0), (-1, 2), 0.8, colors.HexColor(COR_LINHA)),
        ('BACKGROUND', (0, 3), (-1, 3), cor_destaque),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, 2), 5), ('BOTTOMPADDING', (0, 0), (-1, 2), 5),
        ('TOPPADDING', (0, 3), (-1, 3), 9), ('BOTTOMPADDING', (0, 3), (-1, 3), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    obs_texto = dados_pedido.get("observacoes")
    obs_bloco = [Paragraph("OBSERVAÇÕES", st_label), Spacer(1, 3),
                 Paragraph(_esc(obs_texto) if obs_texto else "<font color='#94A3B8'>Sem observações.</font>", st_obs)]
    t_obs = Table([[obs_bloco]], colWidths=[largura - largura_tot - 16])
    t_obs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(COR_LINHA)),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    t_resumo = Table([[t_obs, "", t_tot]], colWidths=[largura - largura_tot - 16, 16, largura_tot])
    t_resumo.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(KeepTogether([t_resumo]))

    # ---------- Condições e assinaturas ----------
    if info_doc["eh_orcamento"]:
        termos = [
            f"Este orçamento tem validade de {VALIDADE_ORCAMENTO_DIAS} dias corridos a partir da data de emissão.",
            "A disponibilidade dos materiais é confirmada somente após a aprovação do orçamento.",
            "Itens marcados como \"a consultar\" terão o valor informado pela Renascer Locações.",
        ]
        rotulo_ass_1, rotulo_ass_2 = "Renascer Locações", "De acordo do cliente"
    else:
        termos = [
            "Conferir os materiais no ato da entrega e da devolução.",
            "Em caso de avaria, perda ou extravio, o cliente responde pelo ressarcimento conforme contrato de locação.",
            "A devolução deve ocorrer na data e no horário combinados.",
        ]
        rotulo_ass_1, rotulo_ass_2 = "Renascer Locações", "Recebido pelo cliente"

    bloco_final = [Paragraph("CONDIÇÕES", st_secao),
                   HRFlowable(width="100%", thickness=0.8, color=colors.HexColor(COR_LINHA), spaceAfter=4)]
    for termo in termos:
        bloco_final.append(Paragraph(termo, st_termo, bulletText="•"))
    bloco_final.append(Spacer(1, 34))

    t_ass = Table([[
        Paragraph(f"______________________________________<br/><b>{rotulo_ass_1}</b>", st_ass),
        Paragraph(f"______________________________________<br/><b>{rotulo_ass_2}</b><br/>{_esc(dados_pedido.get('cliente'))}", st_ass),
    ]], colWidths=[largura / 2, largura / 2])
    t_ass.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    bloco_final.append(t_ass)
    story.append(KeepTogether(bloco_final))

    rodape = f"Renascer Locações e Eventos  |  {info_doc['nome']} Nº {numero}"
    doc.build(story, canvasmaker=_fabrica_canvas_documento(rodape))
    return caminho_final


# ==========================================
# CONTRATO DE LOCAÇÃO INDIVIDUAL
# ==========================================
def gerar_contrato_pedido(dados_pedido, catalogo=None, caminho_saida=None):
    if not caminho_saida:
        cliente_clean = re.sub(r'[^\w\s-]', '', dados_pedido.get('cliente', 'cliente')).strip().replace(' ', '_')
        id_ped = dados_pedido.get('id', '')
        caminho_saida = f"contrato_{id_ped}_{cliente_clean}.pdf" if id_ped else f"contrato_{cliente_clean}.pdf"

    caminho_final = _obter_caminho_final(caminho_saida)
    doc = SimpleDocTemplate(caminho_final, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor("#2C3E50"), alignment=1, spaceAfter=4)
    sub_header_style = ParagraphStyle('SubHeaderStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#7F8C8D"), alignment=1, spaceAfter=15)
    clause_title = ParagraphStyle('ClauseTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#2C3E50"), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#333333"), spaceAfter=6, alignment=4)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, wordWrap='CJK')
    cell_header = ParagraphStyle('CellHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)

    story.append(Paragraph("<b>RENASCER LOCAÇÕES E EVENTOS</b>", header_style))
    story.append(Paragraph("INSTRUMENTO PARTICULAR DE CONTRATO DE LOCAÇÃO DE BENS MÓVEIS", sub_header_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2C3E50"), spaceAfter=12))

    qualificacao_text = f"""
    <b>LOCADOR:</b> RENASCER LOCAÇÕES E EVENTOS, empresa especializada na locação de equipamentos e materiais para eventos.<br/>
    <b>LOCATÁRIO:</b> {dados_pedido.get('cliente', '')}, Telefone: {dados_pedido.get('telefone', '')}, Endereço de Entrega: {dados_pedido.get('endereco', '')}.<br/>
    <b>DATA DO EVENTO / USO:</b> {dados_pedido.get('data_evento', '')}.
    """
    story.append(Paragraph(qualificacao_text, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("CLÁUSULA PRIMEIRA - DAS OBRIGAÇÕES DO LOCADOR", clause_title))
    story.append(Paragraph("1.1. O LOCADOR compromete-se a entregar os materiais e equipamentos em perfeitas condições de uso, higiene e sem avarias, no local pré-estabelecido e dentro do prazo combinado entre as partes.", body_style))
    story.append(Paragraph("1.2. O LOCADOR compromete-se a realizar o recolhimento dos materiais locados na data e no prazo ajustados com o LOCATÁRIO.", body_style))

    t_items_data = [[Paragraph("Qtd", cell_header), Paragraph("Descrição do Material", cell_header), Paragraph("V. Unit", cell_header), Paragraph("V. Total", cell_header)]]
    texto_orc = dados_pedido.get("orcamento", "") or ""
    linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
    subtotal_itens = 0.0

    for linha in linhas:
        match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
        qtd = int(match_qtd.group(1)) if match_qtd else 1
        mat = match_qtd.group(2) if match_qtd else linha
        v_unit, _ = _buscar_preco_catalogo_local(mat, catalogo)
        if v_unit is not None:
            v_tot = v_unit * qtd
            subtotal_itens += v_tot
            u_str = f"R$ {v_unit:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            t_str = f"R$ {v_tot:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        else:
            u_str, t_str = "-", "-"

        t_items_data.append([Paragraph(str(qtd), cell_style), Paragraph(mat, cell_style), Paragraph(u_str, cell_style), Paragraph(t_str, cell_style)])

    t_items = Table(t_items_data, colWidths=[35, 279, 95, 95], repeatRows=1)
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D5D8DC")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9F9")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    try:
        dist_km = float(str(dados_pedido.get("distancia_km", 0.0) or 0.0).replace(',', '.'))
    except ValueError:
        dist_km = 0.0

    try:
        desconto = float(str(dados_pedido.get("desconto", 0.0) or 0.0).replace(',', '.'))
    except ValueError:
        desconto = 0.0

    frete = (dist_km * 4.0) * 1.10
    total_geral = max(0.0, (subtotal_itens + frete) - desconto)

    val_desc_text = f" Subtotal: R$ {subtotal_itens:,.2f} | Frete: R$ {frete:,.2f} | Desconto: R$ {desconto:,.2f} | TOTAL: R$ {total_geral:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
    story.append(Paragraph(f"<b>Resumo Financeiro:</b> {val_desc_text}", body_style))

    story.append(Paragraph("CLÁUSULA SEGUNDA - DAS OBRIGAÇÕES DO LOCATÁRIO", clause_title))
    story.append(Paragraph("2.1. O LOCATÁRIO responsabiliza-se integralmente pela guarda, conservação e correto manuseio dos materiais locados a partir do momento do recebimento até a sua efetiva devolução.", body_style))
    story.append(Paragraph("2.2. Em caso de danos, avarias, destruição parcial ou total, ou perda/extravio dos materiais e equipamentos locados, o LOCATÁRIO compromete-se a ressarcir integralmente o LOCADOR pelos prejuízos causados, com base no valor de mercado ou custo de reposição dos bens.", body_style))

    story.append(Paragraph("CLÁUSULA TERCEIRA - DO CANCELAMENTO E RESCISÃO", clause_title))
    story.append(Paragraph("3.1. O cancelamento da reserva ou do contrato por parte do LOCATÁRIO deverá ser formalizado com antecedência mínima de 7 (sete) dias em relação à data do evento.", body_style))
    story.append(Paragraph("3.2. Caso o cancelamento ocorra em prazo inferior a 7 (sete) dias do evento, será devida pelo LOCATÁRIO uma multa compensatória equivalente a 30% (trinta por cento) sobre o valor total do contrato.", body_style))

    story.append(Paragraph("CLÁUSULA QUARTA - DO DESCUMPRIMENTO E MULTA", clause_title))
    story.append(Paragraph("4.1. O descumprimento injustificado de qualquer das demais obrigações ou prazos pactuados neste instrumento sujeitará a parte infratora ao pagamento de multa moratória/compensatória fixada em 30% (trinta por cento) sobre o valor total do contrato, sem prejuízo da reparação por eventuais perdas e danos.", body_style))

    story.append(Spacer(1, 30))
    t_ass = Table([
        [Paragraph("________________________________________<br/><b>RENASCER LOCAÇÕES</b><br/>Locador", ParagraphStyle('A1', parent=body_style, alignment=1)),
         Paragraph(f"________________________________________<br/><b>{dados_pedido.get('cliente', '')}</b><br/>Locatário", ParagraphStyle('A2', parent=body_style, alignment=1))]
    ], colWidths=[250, 254])
    t_ass.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(KeepTogether(t_ass))

    doc.build(story, canvasmaker=NumberedCanvas)
    return caminho_final


# ==========================================
# GERAÇÃO EM LOTE DA SELEÇÃO [X]
# ==========================================
def gerar_pdfs_em_lote_pedidos(lista_pedidos_selecionados, catalogo=None):
    arquivos_gerados = []
    for ped in lista_pedidos_selecionados:
        caminho = gerar_pdf_pedido(ped, catalogo=catalogo)
        arquivos_gerados.append(caminho)
    return arquivos_gerados


def gerar_pdfs_em_lote_contratos(lista_pedidos_selecionados, catalogo=None):
    arquivos_gerados = []
    for ped in lista_pedidos_selecionados:
        caminho = gerar_contrato_pedido(ped, catalogo=catalogo)
        arquivos_gerados.append(caminho)
    return arquivos_gerados


# =========================================================
# IMPRESSÃO RÁPIDA MÚLTIPLA EM FORMATO REDUZIDO (MEIA FOLHA A4)
# =========================================================

def _montar_card_pedido_compacto(dados_pedido, catalogo, largura_util=539):
    """
    Constrói um card compacto e autocontido de um pedido, otimizado para
    ocupar aproximadamente metade de uma folha A4 com alta legibilidade.
    """
    styles = getSampleStyleSheet()
    title_emp = ParagraphStyle('CTit', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#1E293B'))
    sub_emp = ParagraphStyle('CSub', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748B'))
    num_ped = ParagraphStyle('CNum', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=2, textColor=colors.HexColor('#2563EB'))
    dt_ev = ParagraphStyle('CDt', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=2, textColor=colors.HexColor('#0F172A'))
    txt = ParagraphStyle('CTxt', fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F172A'))
    cell_h = ParagraphStyle('CCellH', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white)
    cell_b = ParagraphStyle('CCellB', fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'))
    cell_c = ParagraphStyle('CCellC', fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=1, textColor=colors.HexColor('#1E293B'))
    cell_r = ParagraphStyle('CCellR', fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=2, textColor=colors.HexColor('#1E293B'))
    txt_tot = ParagraphStyle('CTot', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'))
    txt_ass = ParagraphStyle('CAss', fontName='Helvetica', fontSize=6.5, leading=8.5, textColor=colors.HexColor('#475569'))

    pid = dados_pedido.get('id', '')
    cli = dados_pedido.get('cliente', '') or '-'
    tel = dados_pedido.get('telefone', '') or '-'
    end = dados_pedido.get('endereco', '') or '-'
    dt = dados_pedido.get('data_evento', '') or '-'
    st = dados_pedido.get('tipo', 'Pedido')
    st_fmt = st.replace('Ja', 'Já').replace('Pedido', 'Pendente')
    cor_t = dados_pedido.get('cor_toalha', '')
    obs = dados_pedido.get('observacoes', '')

    # 1. Cabeçalho
    t_head = Table([
        [Paragraph('<b>RENASCER LOCAÇÕES & EVENTOS</b>', title_emp), Paragraph(f'<b>PEDIDO #{pid}</b>', num_ped)],
        [Paragraph('Via de Entrega / Conferência de Carga', sub_emp), Paragraph(f'Data Evento: {dt}', dt_ev)]
    ], colWidths=[largura_util - 160, 160])
    t_head.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0)]))

    # 2. Informações do Cliente & Evento
    col1_txt = f'<b>Cliente:</b> {cli}<br/><b>Telefone:</b> {tel}<br/><b>Endereço:</b> {end}'
    col2_txt = f'<b>Status:</b> {st_fmt}'
    if cor_t:
        col2_txt += f'<br/><b>Cor Toalha:</b> {cor_t}'
    if obs:
        col2_txt += f'<br/><b>Obs:</b> {obs}'

    t_info = Table([
        [Paragraph(col1_txt, txt), Paragraph(col2_txt, txt)]
    ], colWidths=[largura_util * 0.60, largura_util * 0.40])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 4)
    ]))

    # 3. Tabela de Itens Solicitados
    items_data = [[
        Paragraph('<b>[ ]</b>', cell_h),
        Paragraph('<b>Qtd</b>', cell_h),
        Paragraph('<b>Material Solicitado</b>', cell_h),
        Paragraph('<b>V. Unit</b>', cell_h),
        Paragraph('<b>Total</b>', cell_h)
    ]]

    texto_orc = dados_pedido.get('orcamento', '') or ''
    linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
    subtotal_itens = 0.0

    for linha in linhas:
        match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
        qtd = int(match_qtd.group(1)) if match_qtd else 1
        mat = match_qtd.group(2) if match_qtd else linha

        v_unit, _ = _buscar_preco_catalogo_local(mat, catalogo)
        if v_unit is not None:
            v_tot = v_unit * qtd
            subtotal_itens += v_tot
            u_str = f'R$ {v_unit:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
            t_str = f'R$ {v_tot:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
        else:
            u_str, t_str = '-', '-'

        items_data.append([
            Paragraph('[ &nbsp; ]', cell_c),
            Paragraph(str(qtd), cell_c),
            Paragraph(mat, cell_b),
            Paragraph(u_str, cell_r),
            Paragraph(t_str, cell_r)
        ])

    t_items = Table(items_data, colWidths=[24, 34, largura_util - 24 - 34 - 75 - 75, 75, 75])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('PADDING', (0,0), (-1,-1), 2.5)
    ]))

    # 4. Resumo Financeiro
    try:
        dist_km = float(str(dados_pedido.get('distancia_km', 0.0) or 0.0).replace(',', '.'))
    except ValueError:
        dist_km = 0.0

    try:
        desconto = float(str(dados_pedido.get('desconto', 0.0) or 0.0).replace(',', '.'))
    except ValueError:
        desconto = 0.0

    frete = (dist_km * 4.0) * 1.10
    total_geral = max(0.0, (subtotal_itens + frete) - desconto)

    sub_str = f'R$ {subtotal_itens:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
    frete_str = f'R$ {frete:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
    desc_str = f'- R$ {desconto:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
    tot_str = f'R$ {total_geral:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')

    tot_data = [[
        Paragraph(f'Subtotal: {sub_str}', txt),
        Paragraph(f'Frete ({dist_km:.1f} km): {frete_str}', txt),
        Paragraph(f'Desconto: {desc_str}', txt),
        Paragraph(f'<b>TOTAL: {tot_str}</b>', txt_tot)
    ]]
    col_w = largura_util / 4.0
    t_tot = Table(tot_data, colWidths=[col_w, col_w, col_w, col_w])
    t_tot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3)
    ]))

    # 5. Assinatura do Cliente
    ass_data = [[
        Paragraph('Recebido em perfeitas condições por: ___________________________________ Assinatura: _________________________ Data: ___/___/___', txt_ass)
    ]]
    t_ass = Table(ass_data, colWidths=[largura_util])
    t_ass.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 1), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))

    # Montagem do Card externo
    card_elements = [
        [t_head],
        [Spacer(1, 3)],
        [t_info],
        [Spacer(1, 3)],
        [t_items],
        [Spacer(1, 3)],
        [t_tot],
        [Spacer(1, 3)],
        [t_ass]
    ]

    card_table = Table(card_elements, colWidths=[largura_util])
    card_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))

    return card_table


def gerar_impressao_rapida_multipla(lista_pedidos, catalogo=None, caminho_saida=None):
    """
    Gera um PDF único de Impressão Rápida com pedidos em formato reduzido.
    Coloca preferencialmente 2 pedidos por folha A4 (metade de folha A4 para cada pedido)
    com linha de corte tracejada entre eles para facilitar o destaque e uso em entregas.
    Salva o arquivo gerado na pasta PDF do projeto.
    """
    if not lista_pedidos:
        raise ValueError("Nenhum pedido fornecido para impressão rápida.")

    if not caminho_saida:
        data_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        caminho_saida = f"impressao_rapida_{data_str}.pdf"

    caminho_final = _obter_caminho_final(caminho_saida)

    # Margens de 28 pt (10 mm) nas laterais e 22 pt superior/inferior
    doc = SimpleDocTemplate(
        caminho_final,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=22,
        bottomMargin=22
    )

    largura_util = 595.28 - (28 * 2)       # ~539.28 pt
    altura_util_pagina = 841.89 - (22 * 2) # ~797.89 pt

    # Monta cada card de pedido e calcula sua altura
    cards_com_altura = []
    for ped in lista_pedidos:
        card = _montar_card_pedido_compacto(ped, catalogo, largura_util)
        _, h = card.wrap(largura_util, altura_util_pagina)
        cards_com_altura.append((card, h))

    story = []
    i = 0
    total = len(cards_com_altura)

    while i < total:
        card1, h1 = cards_com_altura[i]

        # Se for o último card da lista
        if i == total - 1:
            story.append(card1)
            i += 1
            break

        card2, h2 = cards_com_altura[i + 1]

        # Se os dois cabem juntos em uma folha A4 (com ~28pt de folga para espaçador e linha de corte)
        if (h1 + h2 + 28) <= altura_util_pagina:
            story.append(card1)
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94A3B8"), spaceAfter=4, spaceBefore=2, dash=[4, 4]))
            story.append(card2)
            i += 2
            if i < total:
                story.append(PageBreak())
        else:
            # Não cabem 2 juntos confortavelmente; coloca card1 sozinho na folha
            story.append(card1)
            i += 1
            if i < total:
                story.append(PageBreak())

    doc.build(story)
    return caminho_final
