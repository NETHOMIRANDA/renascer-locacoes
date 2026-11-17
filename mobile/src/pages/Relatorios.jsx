import React, { useEffect, useState } from 'react'
import { buscarTodosPedidosRelatorio } from '../lib/db'
import { moeda, converterFloat } from '../lib/format'

export default function Relatorios({ showToast }) {
  const [dados, setDados] = useState([])
  const [loading, setLoading] = useState(true)
  const [aba, setAba] = useState('resumo')

  async function load() {
    setLoading(true)
    try { setDados(await buscarTodosPedidosRelatorio()) }
    catch (e) { showToast?.('Erro: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  // ---- Resumo por status ----
  const porTipo = {}
  for (const p of dados) {
    porTipo[p.tipo] = (porTipo[p.tipo] || 0) + 1
  }

  // ---- Itens mais locados (parse orcamento text) ----
  const itensMap = {}
  for (const p of dados) {
    if (!p.orcamento) continue
    for (const line of p.orcamento.split('\n')) {
      const l = line.trim()
      if (!l) continue
      const m = l.match(/^(\d+(?:[.,]\d+)?)\s*x?\s*(.+?)\s*\((?:R\$\s*)?([\d.,]+)\)/i)
      if (m) {
        const qtd = Number(m[1].replace(',', '.'))
        const nome = m[2].trim()
        const preco = converterFloat(m[3])
        if (!itensMap[nome]) itensMap[nome] = { qtd: 0, valor: 0 }
        itensMap[nome].qtd += qtd
        itensMap[nome].valor += qtd * preco
      }
    }
  }
  const ranking = Object.entries(itensMap).map(([nome, v]) => ({ nome, ...v })).sort((a, b) => b.qtd - a.qtd)

  // ---- Perdas: não efetivados ----
  const naoEfetivados = dados.filter(p => p.tipo === 'Orcamento' || p.tipo === 'Cancelado')
  const totalPedidos = dados.length
  const taxaPerda = totalPedidos ? (naoEfetivados.length / totalPedidos * 100) : 0

  // ---- Projeção simples: média dos últimos (por criado_em não disponível sempre) ----
  const totalValor = dados.reduce((s, p) => {
    if (!p.orcamento) return s
    let sub = 0
    for (const line of p.orcamento.split('\n')) {
      const m = line.trim().match(/^(\d+(?:[.,]\d+)?)\s*x?\s*.+?\s*\((?:R\$\s*)?([\d.,]+)\)/i)
      if (m) sub += Number(m[1].replace(',', '.')) * converterFloat(m[2])
    }
    return s + sub - (Number(p.desconto) || 0)
  }, 0)

  if (loading) return <div className="empty">Carregando...</div>

  return (
    <div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 10, overflowX: 'auto' }}>
        {[
          { k: 'resumo', l: 'Resumo' },
          { k: 'ranking', l: 'Itens mais locados' },
          { k: 'perdas', l: 'Perdas' },
          { k: 'projecao', l: 'Projeção' },
        ].map(a => (
          <span key={a.k} className={`chip ${aba === a.k ? 'active' : ''}`} onClick={() => setAba(a.k)}>{a.l}</span>
        ))}
      </div>

      {aba === 'resumo' && (
        <div>
          <div className="card">
            <h3 style={{ marginBottom: 8 }}>Resumo por status</h3>
            {Object.entries(porTipo).map(([t, n]) => (
              <div key={t} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 14 }}>
                <span>{t}</span><strong>{n}</strong>
              </div>
            ))}
            {Object.keys(porTipo).length === 0 && <div className="empty">Sem dados</div>}
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 8 }}>Totais</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
              <span>Total de registros</span><strong>{dados.length}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginTop: 4 }}>
              <span>Valor bruto estimado</span><strong style={{ color: 'var(--accent)' }}>{moeda(totalValor)}</strong>
            </div>
          </div>
        </div>
      )}

      {aba === 'ranking' && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Ranking de itens mais locados</h3>
          {ranking.length === 0 && <div className="empty">Sem dados</div>}
          {ranking.slice(0, 20).map((r, i) => (
            <div key={r.nome} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>{i + 1}. {r.nome}</span>
                <strong style={{ fontSize: 13 }}>{r.qtd} un</strong>
              </div>
              <div className="meta">Valor: {moeda(r.valor)}</div>
            </div>
          ))}
        </div>
      )}

      {aba === 'perdas' && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Perdas</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
            <span>Não efetivados (orç/canc)</span><strong>{naoEfetivados.length}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginTop: 4 }}>
            <span>Taxa de perda</span><strong>{taxaPerda.toFixed(1)}%</strong>
          </div>
          <div style={{ marginTop: 8 }}>
            {naoEfetivados.slice(0, 20).map(p => (
              <div key={p.id} className="listitem">
                <div className="title">#{p.id} {p.cliente}</div>
                <div className="meta">{p.tipo} • {p.data_evento || '-'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {aba === 'projecao' && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Projeção (estimativa)</h3>
          <p style={{ fontSize: 13, color: 'var(--muted)' }}>
            Com base em {dados.length} registros e valor bruto de {moeda(totalValor)}, a média por registro é {moeda(dados.length ? totalValor / dados.length : 0)}.
          </p>
          <div style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
              <span>Projeção semanal (7 dias)</span><strong>{moeda(totalValor / 4)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginTop: 4 }}>
              <span>Projeção mensal</span><strong>{moeda(totalValor)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginTop: 4 }}>
              <span>Projeção anual</span><strong>{moeda(totalValor * 12)}</strong>
            </div>
          </div>
        </div>
      )}
      <button className="btn secondary" style={{ marginTop: 10 }} onClick={load}>Atualizar</button>
    </div>
  )
}