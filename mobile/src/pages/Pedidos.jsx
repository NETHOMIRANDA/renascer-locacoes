import React, { useEffect, useState } from 'react'
import PedidoForm from '../components/PedidoForm'
import { buscarPorStatus, buscarPorId, inserirPedido, atualizarPedido, alterarStatus, alterarStatusMultiplos } from '../lib/db'
import { moeda } from '../lib/format'
import { gerarPdfPedido } from '../lib/pdf'

const STATUS_LABEL = {
  'Pedido': 'Pedido',
  'Ja Entregue': 'Entregue',
  'Ja Recolhido': 'Recolhido',
  'Arquivado': 'Arquivado',
}

export default function Pedidos({ showToast }) {
  const [lista, setLista] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [isNew, setIsNew] = useState(false)
  const [filtroStatus, setFiltroStatus] = useState('Todos')
  const [filtro, setFiltro] = useState('')

  async function load() {
    setLoading(true)
    try {
      setLista(await buscarPorStatus('Pedido'))
    } catch (e) { showToast?.('Erro: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtrada = lista.filter(r => {
    if (filtro && !(r.cliente || '').toLowerCase().includes(filtro.toLowerCase())) return false
    if (filtroStatus !== 'Todos' && r.tipo !== filtroStatus) return false
    return true
  })

  async function handleSave(dados) {
    try {
      if (dados.id) {
        await atualizarPedido(dados.id, dados)
        showToast?.('Pedido atualizado')
      } else {
        const id = await inserirPedido(dados, 'Pedido')
        showToast?.(`Pedido #${id} salvo`)
      }
      setEditing(null); setIsNew(false)
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function mudarStatus(id, novo) {
    try {
      await alterarStatus(id, novo)
      showToast?.('Status atualizado')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function direcionarOrcamento(id) {
    if (!confirm('Direcionar de volta para orçamento?')) return
    try {
      await alterarStatus(id, 'Orcamento')
      showToast?.('Direcionado para orçamento')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  if (editing || isNew) {
    return (
      <div>
        <h3 style={{ marginBottom: 10 }}>{isNew ? 'Novo Pedido' : `Editar Pedido #${editing?.id}`}</h3>
        <PedidoForm initial={isNew ? null : editing} onSave={handleSave} onCancel={() => { setEditing(null); setIsNew(false) }} />
      </div>
    )
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <input className="input" placeholder="Buscar cliente..." value={filtro} onChange={e => setFiltro(e.target.value)} style={{ flex: 1 }} />
        <button className="btn sm" onClick={() => setIsNew(true)}>+ Novo</button>
      </div>
      <div style={{ marginBottom: 10, display: 'flex', gap: 6, overflowX: 'auto' }}>
        {['Todos', 'Pedido', 'Ja Entregue', 'Ja Recolhido', 'Arquivado'].map(s => (
          <span key={s} className={`chip ${filtroStatus === s ? 'active' : ''}`} onClick={() => setFiltroStatus(s)}>
            {s === 'Todos' ? 'Todos' : STATUS_LABEL[s]}
          </span>
        ))}
      </div>
      {loading && <div className="empty">Carregando...</div>}
      {!loading && filtrada.length === 0 && <div className="empty">Nenhum pedido</div>}
      {filtrada.map(r => (
        <div key={r.id} className="listitem">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="title">#{r.id} {r.cliente}</div>
            <span className={`badge ${r.tipo === 'Pedido' ? 'ped' : r.tipo === 'Cancelado' ? 'can' : 'ent'}`}>{STATUS_LABEL[r.tipo] || r.tipo}</span>
          </div>
          <div className="meta">{r.telefone || '-'} • {r.data_evento || '-'}</div>
          <div className="meta" style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button className="btn sm ghost" onClick={async () => { const d = await buscarPorId(r.id); setEditing(d) }}>Editar</button>
            <button className="btn sm" style={{ background: '#0F766E' }} onClick={async () => { const d = await buscarPorId(r.id); gerarPdfPedido(d) }}>PDF</button>
            {r.tipo === 'Pedido' && (
              <>
                <button className="btn sm" onClick={() => mudarStatus(r.id, 'Ja Entregue')}>Entregue</button>
                <button className="btn sm" style={{ background: '#7C3AED' }} onClick={() => mudarStatus(r.id, 'Ja Recolhido')}>Recolhido</button>
              </>
            )}
            {r.tipo === 'Ja Entregue' && (
              <button className="btn sm" style={{ background: '#7C3AED' }} onClick={() => mudarStatus(r.id, 'Ja Recolhido')}>Recolhido</button>
            )}
            <button className="btn sm" style={{ background: '#64748B' }} onClick={() => mudarStatus(r.id, 'Arquivado')}>Arquivar</button>
            <button className="btn sm ghost" onClick={() => direcionarOrcamento(r.id)}>→ Orçamento</button>
          </div>
        </div>
      ))}
    </div>
  )
}