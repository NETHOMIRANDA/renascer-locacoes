import io
import os
import traceback
from flask import Flask, make_response, request, jsonify

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

app = Flask(__name__)


# ==========================================
# FUNÇÕES DE TRATAMENTO DE DADOS
# ==========================================

def converter_para_float(val):
    """
    Converte valores para float de forma segura, tratando números e strings
    formatadas em moeda brasileira (ex: 'R$ 14,00' -> 14.0).
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val_clean = val.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(val_clean)
        except ValueError:
            return 0.0
    return 0.0


def formatar_moeda(valor):
    """
    Formata valores para o padrão de moeda brasileira (R$ X.XXX,XX).
    """
    valor_float = converter_para_float(valor)
    return f"R$ {valor_float:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')


# ==========================================
# MOTOR DE GERAÇÃO DO PDF (REPORTLAB)
# ==========================================

def criar_pdf_em_memoria(dados_pedido, itens_detalhados):
    """
    Gera o PDF em um buffer em memória (BytesIO) e retorna os bytes do arquivo.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()

    # Estilos Tipográficos
    style_titulo = ParagraphStyle(
        'TituloEmpresa',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#1E293B'),
        alignment=1,
        spaceAfter=4
    )

    style_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#2563EB'),
        alignment=1,
        spaceAfter=10
    )

    style_texto = ParagraphStyle(
        'TextoInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor('#0F172A')
    )

    style_item_tabela = ParagraphStyle(
        'ItemTabela',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#1E293B')
    )

    style_cabecalho_tabela = ParagraphStyle(
        'CabecalhoTabela',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )

    elements = []

    # 1. Cabeçalho
    elements.append(Paragraph("RENASCER LOCAÇÕES", style_titulo))
    elements.append(Paragraph("COMPROVANTE DE PEDIDO E RECIBO DE LOCAÇÃO", style_subtitulo))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E293B'), spaceAfter=10))

    # 2. Informações do Cliente e Evento
    info_cliente = [
        [
            Paragraph(f"<b>Cliente:</b> {dados_pedido.get('cliente', '-')}", style_texto),
            Paragraph(f"<b>Telefone:</b> {dados_pedido.get('telefone', '-')}", style_texto)
        ],
        [
            Paragraph(f"<b>Endereço:</b> {dados_pedido.get('endereco', '-')}", style_texto),
            Paragraph(f"<b>Data do Evento:</b> {dados_pedido.get('data_evento', '-')}", style_texto)
        ]
    ]

    t_info = Table(info_cliente, colWidths=[10.5 * cm, 8.0 * cm])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # 3. Tabela de Materiais
    tabela_dados = [[
        Paragraph("<b>Qtd</b>", style_cabecalho_tabela),
        Paragraph("<b>Material Solicitado</b>", style_cabecalho_tabela),
        Paragraph("<b>Valor Unit.</b>", style_cabecalho_tabela),
        Paragraph("<b>Total</b>", style_cabecalho_tabela)
    ]]

    for item in itens_detalhados:
        v_unit = converter_para_float(item.get('v_unit', 0))
        v_tot = converter_para_float(item.get('v_total', 0))

        tabela_dados.append([
            Paragraph(str(item.get('qtd', '1')), style_item_tabela),
            Paragraph(str(item.get('descricao', '')), style_item_tabela),
            Paragraph(formatar_moeda(v_unit), style_item_tabela),
            Paragraph(formatar_moeda(v_tot), style_item_tabela)
        ])

    t_itens = Table(tabela_dados, colWidths=[1.5 * cm, 10.5 * cm, 3.0 * cm, 3.5 * cm])
    t_itens.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_itens)
    elements.append(Spacer(1, 10))

    # 4. Resumo de Valores
    subtotal = converter_para_float(dados_pedido.get('subtotal', 0))
    frete = converter_para_float(dados_pedido.get('frete', 0))
    desconto = converter_para_float(dados_pedido.get('desconto', 0))
    distancia_km = converter_para_float(dados_pedido.get('distancia_km', 0))

    total_geral = max(0.0, (subtotal + frete) - desconto)
    texto_frete = f"Frete ({distancia_km:.1f} km):" if distancia_km > 0 else "Frete:"

    resumo_dados = [
        ["Subtotal dos Itens:", formatar_moeda(subtotal)],
        [texto_frete, formatar_moeda(frete)],
        ["Desconto Concedido:", f"- {formatar_moeda(desconto)}"],
        ["TOTAL GERAL:", formatar_moeda(total_geral)]
    ]

    t_resumo = Table(resumo_dados, colWidths=[12.5 * cm, 6.0 * cm])
    t_resumo.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 9),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2563EB')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_resumo)
    elements.append(Spacer(1, 25))

    # 5. Campo de Assinatura
    t_assinatura = Table([
        ["__________________________________________________"],
        ["Assinatura do Cliente / Responsável pelo Recebimento"]
    ], colWidths=[18.5 * cm])
    t_assinatura.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#64748B'))
    ]))
    elements.append(t_assinatura)

    # Compila o PDF na memória
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


# ==========================================
# ROTAS FLASK PARA EMISSÃO DO PDF
# ==========================================

@app.route('/gerar-pdf-exemplo', methods=['GET'])
def emitir_pdf_exemplo():
    """
    Rota GET para testar a geração direta no navegador.
    """
    try:
        dados_pedido = {
            'cliente': 'Gabriel Viana',
            'telefone': '6298178178',
            'endereco': 'Academia Parque Amazonas',
            'data_evento': '11/09/2026',
            'subtotal': 440.00,
            'frete': 0.00,
            'desconto': 0.00,
            'distancia_km': 0.0
        }

        itens_detalhados = [
            {'qtd': 7, 'descricao': 'Mesa com 4 Cadeiras de Plástico (Branca)', 'v_unit': 14.00, 'v_total': 98.00},
            {'qtd': 100, 'descricao': 'Cadeira de plástico branca', 'v_unit': 3.00, 'v_total': 300.00},
            {'qtd': 7, 'descricao': 'Toalha Quadrada para 4 Lugares (1,50m x 1,50m)', 'v_unit': 6.00, 'v_total': 42.00}
        ]

        pdf_bytes = criar_pdf_em_memoria(dados_pedido, itens_detalhados)

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=pedido_Gabriel_Viana.pdf'
        return response

    except Exception as e:
        print("--- ERRO NA GERAÇÃO DO PDF ---")
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


@app.route('/gerar-pdf', methods=['POST'])
def emitir_pdf_post():
    """
    Rota POST para receber dados dinâmicos via JSON.
    """
    try:
        req_data = request.get_json() or {}
        dados_pedido = req_data.get('dados_pedido', {})
        itens_detalhados = req_data.get('itens_detalhados', [])

        pdf_bytes = criar_pdf_em_memoria(dados_pedido, itens_detalhados)

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=comprovante_pedido.pdf'
        return response

    except Exception as e:
        print("--- ERRO NA GERAÇÃO DO PDF ---")
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    # Executa a aplicação localmente na porta 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
