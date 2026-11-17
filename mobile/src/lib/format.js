export function moeda(v) {
  const n = Number(v) || 0
  return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function converterFloat(val) {
  if (typeof val === 'number') return val
  if (typeof val === 'string') {
    const c = val.replace(/R\$/g, '').replace(/\s/g, '').replace(/\./g, '').replace(',', '.')
    const n = parseFloat(c)
    return isNaN(n) ? 0 : n
  }
  return 0
}

export function dataHoje() {
  const d = new Date()
  return d.toLocaleDateString('pt-BR')
}

export function normalizarNome(t) {
  return (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/\s+/g, ' ')
}