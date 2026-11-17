import React, { useState, useEffect } from 'react'
import { buscarCatalogo, buscarClientes } from '../lib/db'
import { moeda, converterFloat } from '../lib/format'

export default function PedidoForm({ initial, onSave, onCancel }) {
  const [cliente, setCliente] = useState(initial?.cliente || '')
  const [telefone, setTelefone] = useState(initial?.telefone || '')
  const [endereco, setEndereco] = useState(initial?.endereco || '')
  const [dataEvento, setDataEvento] = useState(initial?.data_evento || '')
  const [distancia, setDistancia] = useState(initial?.distancia_km ?? 0)
  const [desconto, setDesconto] = useState(initial?.desconto ?? 0)
  const [observacoes, setObservacoes] = useState(initial?.observacoes || '')
  const [itens, setItens] = useState([]) // {nome, qtd, v_unit}
  const [catalogo, setCatalogo] = useState([])
  const [clientesSug, setClientesSug] = useState([])
  const [showCat, setShowCat] = useState(false)
  const [showCli, setShowCli] = useState(false)
  const [catBusca, setCatBusca] = useState('')

  useEffect(() => {
    buscarCatalogo().then(setCatalogo).catch(() => {})
  }, [])

  // parse initial orcamento text into items (best effort)
  useEffect(() => {
    if (initial?.orcamento && itens.length === 0) {
      const lines = initial.orcamento.split('\n').map(l => l.trim()).filter(Boolean)
      const parsed = lines.map(l => {
        const m = l.match(/^(\d+(?:[.,]\d+)?)\s*x?\s*(.+?)\s*\((?:R\$\s*)?([\d.,]+)\)/i)
        if (m) {
          return { nome: m[2].trim(), qtd: Number(m[1].replace(',', '.')), v_unit: converterFloat(m[3]) }
        }
        return { nome: l, qtd: 1, v_unit: 0 }
      })
      setItens(parsed)
    }
  }, [initial])

  async function buscarCli(termo) {
    setCliente(termo)
    if (termo.length >= 2) {
      try { setClientesSug(await buscarClientes(termo, 8)) } catch (e) { setClientesSug([]) }
    } else {
      setClientesSug([])
    }
  }

  function selecionarCliente(c) {
    setCliente(c.nome)
    setTelefone(c.telefone || '')
    setEndereco(c.endereco || '')
    setClientesSug([])
    setShowCli(false)
  }

  function addItemCat(cat) {
    setItens(prev => [...prev, { nome: cat.nome, qtd: 1, v_unit: cat.preco }])
    setShowCat(false)
    setCatBusca('')
  }

  function addItemManual() {
    setItens(prev => [...prev, { nome: '', qtd: 1, v_unit: 0 }])
  }

  function updateItem(idx, field, value) {
    setItens(prev => prev.map((it, i) => i === idx ? { ...it, [field]: value } : it))
  }

  function removeItem(idx) {
    setItens(prev => prev.filter((_, i) => i !== idx))
  }

  function serializar() {
    return itens.map(it => `${it.qtd}x ${it.nome} (R$ ${Number(it.v_unit).toFixed(2)})`).join('\n')
  }

  function subtotal() {
    return itens.reduce((s, it) => s + (Number(it.qtd) || 0) * (Number(it.v_unit) || 0), 0)
  }

  async function salvar() {
    if (!cliente.trim()) {
      alert('Informe o cliente')
      return
    }
    const dados = {
      cliente: cliente.trim(),
      telefone: telefone.trim(),
      endereco: endereco.trim(),
      data_evento: dataEvento.trim(),
      distancia_km: Number(distancia) || 0,
      desconto: Number(desconto) || 0,
      observacoes: observacoes.trim(),
      orcamento: serializar(),
    }
    if (initial?.id) dados.id = initial.id
    await onSave(dados)
  }

  const filtrado = catalogo.filter(c => !catBusca || c.nome.toLowerCase().includes(catBusca.toLowerCase()) || (c.categoria || '').toLowerCase().includes(catBusca.toLowerCase()))

  return (
    <div>
      <div className="field">
        <label className="label">Cliente</label>
        <input className="input" value={cliente} onChange={e => buscarCli(e.target.value)} placeholder="Digite para buscar..." />
        {clientesSug.length > 0 && (
          <div style={{ marginTop: 4 }}>
            {clientesSug.map(c => (
              <div key={c.id} className="listitem" style={{ cursor: 'pointer', padding: 8 }} onClick={() => selecionarCliente(c)}>
                <div className="title">{c.nome}</div>
                <div className="meta">{c.telefone || ''}</div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="row">
        <div className="field" style={{ flex: 1 }}>
          <label className="label">Telefone</label>
          <input className="input" value={telefone} onChange={e => setTelefone(e.target.value)} />
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label className="label">Data evento</label>
          <input className="input" value={dataEvento} onChange={e => setDataEvento(e.target.value)} placeholder="dd/mm/aaaa" />
        </div>
      </div>
      <div className="field">
        <label className="label">Endereço</label>
        <input className="input" value={endereco} onChange={e => setEndereco(e.target.value)} />
      </div>

      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>Itens</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn sm ghost" onClick={() => setShowCat(true)}>+ Catálogo</button>
          <button className="btn sm ghost" onClick={addItemManual}>+ Manual</button>
        </div>
      </div>
      {itens.length === 0 && <div className="empty" style={{ padding: 10 }}>Nenhum item adicionado</div>}
      {itens.map((it, idx) => (
        <div key={idx} className="listitem">
          <input className="input" placeholder="Descrição do item" value={it.nome} onChange={e => updateItem(idx, 'nome', e.target.value)} style={{ marginBottom: 6 }} />
          <div className="row">
            <div style={{ flex: 1 }}>
              <label className="label">Qtd</label>
              <input className="input" type="number" value={it.qtd} onChange={e => updateItem(idx, 'qtd', e.target.value)} />
            </div>
            <div style={{ flex: 2 }}>
              <label className="label">Valor unit.</label>
              <input className="input" type="number" step="0.01" value={it.v_unit} onChange={e => updateItem(idx, 'v_unit', e.target.value)} />
            </div>
            <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end' }}>
              <button className="btn sm danger" onClick={() => removeItem(idx)}>✕</button>
            </div>
          </div>
          <div className="meta" style={{ marginTop: 4 }}>Total: {moeda((Number(it.qtd) || 0) * (Number(it.v_unit) || 0))}</div>
        </div>
      ))}

      <div className="row">
        <div className="field" style={{ flex: 1 }}>
          <label className="label">Distância (km) - frete</label>
          <input className="input" type="number" step="0.1" value={distancia} onChange={e => setDistancia(e.target.value)} />
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label className="label">Desconto (R$)</label>
          <input className="input" type="number" step="0.01" value={desconto} onChange={e => setDesconto(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label className="label">Observações</label>
        <textarea className="input" rows={2} value={observacoes} onChange={e => setObservacoes(e.target.value)} />
      </div>

      <div className="card" style={{ background: '#F8FAFC' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
          <span>Subtotal itens:</span><strong>{moeda(subtotal())}</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginTop: 4 }}>
          <span>Total geral (aprox.):</span><strong style={{ color: 'var(--accent)' }}>{moeda(Math.max(0, subtotal() + 0 - (Number(desconto) || 0)))}</strong>
        </div>
      </div>

      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn secondary" onClick={onCancel} style={{ flex: 1 }}>Cancelar</button>
        <button className="btn" onClick={salvar} style={{ flex: 1 }}>Salvar</button>
      </div>

      {showCat && (
        <div className="modal-back" onClick={() => setShowCat(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Selecionar do catálogo</h3>
            <input className="input" placeholder="Buscar item..." value={catBusca} onChange={e => setCatBusca(e.target.value)} style={{ marginBottom: 8 }} />
            <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
              {filtrado.slice(0, 50).map(c => (
                <div key={c.id} className="listitem" style={{ cursor: 'pointer' }} onClick={() => addItemCat(c)}>
                  <div className="title">{c.nome}</div>
                  <div className="meta">{c.categoria} • {moeda(c.preco)} • estoque {c.estoque}</div>
                </div>
              ))}
              {filtrado.length === 0 && <div className="empty">Nenhum item</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}