import React, { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import { buscarClientes, salvarCliente, excluirCliente, encontrarClienteSimilar } from '../lib/db'

export default function Clientes({ showToast }) {
  const [lista, setLista] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('')
  const [editing, setEditing] = useState(null) // {id,nome,telefone,endereco} or null
  const [isNew, setIsNew] = useState(false)

  async function load() {
    setLoading(true)
    try { setLista(await buscarClientes(filtro, 1000)) }
    catch (e) { showToast?.('Erro: ' + e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filtro])

  async function salvar() {
    if (!editing?.nome?.trim()) { showToast?.('Informe o nome'); return }
    try {
      const res = await salvarCliente(editing)
      if (!res.ok) { showToast?.(res.msg); return }
      showToast?.(res.msg)
      setEditing(null); setIsNew(false)
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  async function excluir(id) {
    if (!confirm('Excluir este cliente?')) return
    try {
      await excluirCliente(id)
      showToast?.('Cliente excluído')
      load()
    } catch (e) { showToast?.('Erro: ' + e.message) }
  }

  function novo() {
    setEditing({ id: null, nome: '', telefone: '', endereco: '' })
    setIsNew(true)
  }

  if (editing || isNew) {
    return (
      <div>
        <h3 style={{ marginBottom: 10 }}>{isNew ? 'Novo Cliente' : 'Editar Cliente'}</h3>
        <div className="field">
          <label className="label">Nome</label>
          <input className="input" value={editing.nome} onChange={e => setEditing({ ...editing, nome: e.target.value })} />
        </div>
        <div className="field">
          <label className="label">Telefone</label>
          <input className="input" value={editing.telefone || ''} onChange={e => setEditing({ ...editing, telefone: e.target.value })} />
        </div>
        <div className="field">
          <label className="label">Endereço</label>
          <input className="input" value={editing.endereco || ''} onChange={e => setEditing({ ...editing, endereco: e.target.value })} />
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
        <input className="input" placeholder="Buscar nome ou telefone..." value={filtro} onChange={e => setFiltro(e.target.value)} style={{ flex: 1 }} />
        <button className="btn sm" onClick={novo}>+ Novo</button>
      </div>
      {loading && <div className="empty">Carregando...</div>}
      {!loading && lista.length === 0 && <div className="empty">Nenhum cliente</div>}
      {lista.map(c => (
        <div key={c.id} className="listitem">
          <div className="title">{c.nome}</div>
          <div className="meta">{c.telefone || '-'} • {c.endereco || '-'}</div>
          <div className="meta" style={{ marginTop: 6, display: 'flex', gap: 6 }}>
            <button className="btn sm ghost" onClick={() => { setEditing({ id: c.id, nome: c.nome, telefone: c.telefone, endereco: c.endereco }); setIsNew(false) }}>Editar</button>
            <button className="btn sm danger" onClick={() => excluir(c.id)}>Excluir</button>
          </div>
        </div>
      ))}
    </div>
  )
}