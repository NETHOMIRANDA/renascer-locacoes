import React, { useEffect, useState } from 'react'
import { buscarCatalogo, salvarItemCatalogo, excluirItemCatalogo } from '../lib/db'
import { moeda } from '../lib/format'

export default function Catalogo({ showToast }) {
  const [lista, setLista] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('')
  const [editing, setEditing] = useState(null)
  const [isNew, setIsNew] = useState(false)

  async function load() {
    setLoading(true)
    try { setLista(await buscarCatalogo()) }
    catch (e) { showToast?.('Erro: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtrada = lista.filter(c => !filtro || c.nome.toLowerCase().includes(filtro.toLowerCase()) || (c.categoria || '').toLowerCase().includes(filtro.toLowerCase()))

  async function salvar() {
    if (!editing?.nome?.trim()) { showToast?.('Informe o nome'); return }
    try {
      await salvarItemCatalogo(editing)
      showToast?.('Item salvo')
      setEditing(null); setIsNew(false)
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function excluir(id) {
    if (!confirm('Excluir este item do catálogo?')) return
    try {
      await excluirItemCatalogo(id)
      showToast?.('Item excluído')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  function novo() {
    setEditing({ id: null, categoria: '', nome: '', unidade: 'Unidade', preco: 0, estoque: 0 })
    setIsNew(true)
  }

  if (editing || isNew) {
    return (
      <div>
        <h3 style={{ marginBottom: 10 }}>{isNew ? 'Novo Item' : 'Editar Item'}</h3>
        <div className="field">
          <label className="label">Categoria</label>
          <input className="input" value={editing.categoria || ''} onChange={e => setEditing({ ...editing, categoria: e.target.value })} />
        </div>
        <div className="field">
          <label className="label">Nome</label>
          <input className="input" value={editing.nome || ''} onChange={e => setEditing({ ...editing, nome: e.target.value })} />
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label className="label">Unidade</label>
            <input className="input" value={editing.unidade || ''} onChange={e => setEditing({ ...editing, unidade: e.target.value })} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label className="label">Preço (R$)</label>
            <input className="input" type="number" step="0.01" value={editing.preco ?? 0} onChange={e => setEditing({ ...editing, preco: e.target.value })} />
          </div>
        </div>
        <div className="field">
          <label className="label">Estoque</label>
          <input className="input" type="number" value={editing.estoque ?? 0} onChange={e => setEditing({ ...editing, estoque: e.target.value })} />
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn secondary" onClick={() => { setEditing(null); setIsNew(false) }} style={{ flex: 1 }}>Cancelar</button>
          <button className="btn" onClick={salvar} style={{ flex: 1 }}>Salvar</button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <input className="input" placeholder="Buscar item..." value={filtro} onChange={e => setFiltro(e.target.value)} style={{ flex: 1 }} />
        <button className="btn sm" onClick={novo}>+ Novo</button>
      </div>
      {loading && <div className="empty">Carregando...</div>}
      {!loading && filtrada.length === 0 && <div className="empty">Nenhum item</div>}
      {filtrada.map(c => (
        <div key={c.id} className="listitem">
          <div className="title">{c.nome}</div>
          <div className="meta">{c.categoria} • {moeda(c.preco)} • estoque {c.estoque}</div>
          <div className="meta" style={{ marginTop: 6, display: 'flex', gap: 6 }}>
            <button className="btn sm ghost" onClick={() => { setEditing({ ...c }); setIsNew(false) }}>Editar</button>
            <button className="btn sm danger" onClick={() => excluir(c.id)}>Excluir</button>
          </div>
        </div>
      ))}
    </div>
  )
}