import React, { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import PedidoForm from '../components/PedidoForm'
import { buscarPorStatus, buscarPorId, inserirPedido, atualizarPedido, alterarStatus } from '../lib/db'
import { moeda } from '../lib/format'
import { gerarPdfPedido } from '../lib/pdf'

export default function Orcamentos({ showToast }) {
  const [lista, setLista] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // null=list, object=editing/new
  const [isNew, setIsNew] = useState(false)
  const [viewing, setViewing] = useState(null)
  const [filtro, setFiltro] = useState('')

  async function load() {
    setLoading(true)
    try {
      setLista(await buscarPorStatus('Orcamento'))
    } catch (e) { showToast?.('Erro: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtrada = lista.filter(r => !filtro || (r.cliente || '').toLowerCase().includes(filtro.toLowerCase()))

  async function handleSave(dados) {
    try {
      if (dados.id) {
        await atualizarPedido(dados.id, dados)
        showToast?.('Orçamento atualizado')
      } else {
        const id = await inserirPedido(dados, 'Orcamento')
        showToast?.(`Orçamento #${id} salvo`)
      }
      setEditing(null); setIsNew(false)
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function moverParaPedido(id) {
    if (!confirm('Enviar para gestão de entrega?')) return
    try {
      await alterarStatus(id, 'Pedido')
      showToast?.('Enviado para pedidos')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function cancelar(id) {
    if (!confirm('Marcar como cancelado?')) return
    try {
      await alterarStatus(id, 'Cancelado')
      showToast?.('Cancelado')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  if (editing || isNew) {
    return (
      <div>
        <h3 style={{ marginBottom: 10 }}>{isNew ? 'Novo Orçamento' : `Editar Orçamento #${editing?.id}`}</h3>
        <PedidoForm initial={isNew ? null : editing} onSave={handleSave} onCancel={() => { setEditing(null); setIsNew(false) }} />
      </div>
    )
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <input className="input" placeholder="Buscar cliente..." value={filtro} onChange={e => setFiltro(e.target.value)} style={{ flex: 1 }} />
        <button className="btn sm" onClick={() => setIsNew(true)}>+ Novo</button>
      </div>
      {loading && <div className="empty">Carregando...</div>}
      {!loading && filtrada.length === 0 && <div className="empty">Nenhum orçamento</div>}
      {filtrada.map(r => (
        <div key={r.id} className="listitem">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="title">#{r.id} {r.cliente}</div>
            <span className="badge orc">Orçamento</span>
          </div>
          <div className="meta">{r.telefone || '-'} • {r.data_evento || '-'}</div>
          <div className="meta" style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button className="btn sm ghost" onClick={async () => { const d = await buscarPorId(r.id); setEditing(d) }}>Editar</button>
            <button className="btn sm" style={{ background: '#0F766E' }} onClick={async () => { const d = await buscarPorId(r.id); gerarPdfPedido(d) }}>PDF</button>
            <button className="btn sm" onClick={() => moverParaPedido(r.id)}>→ Pedido</button>
            <button className="btn sm danger" onClick={() => cancelar(r.id)}>Cancelar</button>
          </div>
        </div>
      ))}
    </div>
  )
}