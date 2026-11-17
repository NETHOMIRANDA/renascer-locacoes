import React, { useEffect, useState } from 'react'
import { buscarPorStatus, buscarTodosPedidosRelatorio } from '../lib/db'
import { moeda } from '../lib/format'

export default function Dashboard({ showToast }) {
  const [stats, setStats] = useState({ orc: 0, ped: 0, can: 0, total: 0 })
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const [orc, ped, can, todos] = await Promise.all([
        buscarPorStatus('Orcamento'),
        buscarPorStatus('Pedido'),
        buscarPorStatus('Cancelado'),
        buscarTodosPedidosRelatorio(),
      ])
      const total = todos.reduce((s, p) => s + (Number(p.desconto) ? 0 : 0), 0)
      setStats({ orc: orc.length, ped: ped.length, can: can.length, total: todos.length })
    } catch (e) {
      showToast?.('Erro: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="empty">Carregando...</div>

  return (
    <div>
      <div className="row">
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#92400E' }}>{stats.orc}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Orçamentos</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#1E40AF' }}>{stats.ped}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Pedidos</div>
        </div>
      </div>
      <div className="row">
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#991B1B' }}>{stats.can}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Cancelados</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--primary)' }}>{stats.total}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Total registros</div>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 6 }}>Bem-vindo!</h3>
        <p style={{ fontSize: 13, color: 'var(--muted)' }}>
          Use as abas abaixo para gerenciar orçamentos, pedidos, clientes, catálogo e relatórios.
          Os dados são sincronizados com o Supabase (mesmo banco do sistema desktop).
        </p>
      </div>
      <button className="btn secondary" onClick={load}>Atualizar</button>
    </div>
  )
}