import jsPDF from 'jspdf'
import 'jspdf-autotable'
import { moeda, converterFloat } from './format'

export function gerarPdfPedido(dados) {
  const doc = new jsPDF()
  const itens = (dados.orcamento || '').split('\n').map(l => l.trim()).filter(Boolean).map(l => {
    const m = l.match(/^(\d+(?:[.,]\d+)?)\s*x?\s*(.+?)\s*\((?:R\$\s*)?([\d.,]+)\)/i)
    if (m) return { qtd: m[1], desc: m[2].trim(), unit: converterFloat(m[3]), total: Number(m[1].replace(',', '.')) * converterFloat(m[3]) }
    return { qtd: '1', desc: l, unit: 0, total: 0 }
  })

  doc.setFontSize(16)
  doc.text('RENASCER LOCAÇÕES', 105, 15, { align: 'center' })
  doc.setFontSize(10)
  doc.text('COMPROVANTE DE PEDIDO E RECIBO DE LOCAÇÃO', 105, 22, { align: 'center' })
  doc.line(14, 26, 196, 26)

  let y = 32
  doc.setFontSize(9)
  doc.text(`Cliente: ${dados.cliente || '-'}`, 14, y); y += 5
  doc.text(`Telefone: ${dados.telefone || '-'}`, 14, y); y += 5
  doc.text(`Endereço: ${dados.endereco || '-'}`, 14, y); y += 5
  doc.text(`Data do Evento: ${dados.data_evento || '-'}`, 14, y); y += 8

  const rows = itens.map(it => [it.qtd, it.desc, moeda(it.unit), moeda(it.total)])
  doc.autoTable({
    startY: y,
    head: [['Qtd', 'Material', 'Vlr Unit.', 'Total']],
    body: rows,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [30, 41, 59] },
  })
  y = doc.lastAutoTable.finalY + 6

  const subtotal = itens.reduce((s, it) => s + it.total, 0)
  const frete = 0
  const desconto = Number(dados.desconto) || 0
  const total = Math.max(0, subtotal + frete - desconto)

  doc.text(`Subtotal: ${moeda(subtotal)}`, 14, y); y += 5
  if (dados.distancia_km) { doc.text(`Frete (${dados.distancia_km} km): ${moeda(0)}`, 14, y); y += 5 }
  doc.text(`Desconto: - ${moeda(desconto)}`, 14, y); y += 5
  doc.setFontSize(11)
  doc.text(`TOTAL GERAL: ${moeda(total)}`, 14, y); y += 8
  doc.setFontSize(9)
  doc.text('__________________________________________________', 105, y + 10, { align: 'center' })
  doc.text('Assinatura do Cliente / Responsável', 105, y + 15, { align: 'center' })

  doc.save(`pedido_${dados.id || 'novo'}_${(dados.cliente || '').replace(/\s/g, '_')}.pdf`)
}