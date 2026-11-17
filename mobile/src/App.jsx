import React, { useState, useEffect } from 'react'
import { isConfigured } from './lib/store'
import ConfigScreen from './components/ConfigScreen'
import Dashboard from './pages/Dashboard'
import Orcamentos from './pages/Orcamentos'
import Pedidos from './pages/Pedidos'
import Clientes from './pages/Clientes'
import Catalogo from './pages/Catalogo'
import Relatorios from './pages/Relatorios'

const TABS = [
  { key: 'home', label: 'Início', icon: '🏠', comp: Dashboard },
  { key: 'orc', label: 'Orçamentos', icon: '📋', comp: Orcamentos },
  { key: 'ped', label: 'Pedidos', icon: '🚚', comp: Pedidos },
  { key: 'cli', label: 'Clientes', icon: '👥', comp: Clientes },
  { key: 'cat', label: 'Catálogo', icon: '📦', comp: Catalogo },
  { key: 'rel', label: 'Relatórios', icon: '📊', comp: Relatorios },
]

export default function App() {
  const [configured, setConfigured] = useState(isConfigured())
  const [tab, setTab] = useState('home')
  const [toast, setToast] = useState(null)

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  if (!configured) {
    return <ConfigScreen onDone={() => setConfigured(true)} showToast={showToast} />
  }

  const Active = TABS.find(t => t.key === tab).comp
  return (
    <div className="app">
      <div className="header">
        <div>
          <div>Renascer Locações</div>
          <div className="sub">Gestão mobile</div>
        </div>
        <button className="btn sm ghost" style={{ width: 'auto' }} onClick={() => setConfigured(false)}>⚙️</button>
      </div>
      <div className="content">
        <Active showToast={showToast} />
      </div>
      <nav className="bottomnav">
        {TABS.map(t => (
          <button key={t.key} className={tab === t.key ? 'active' : ''} onClick={() => setTab(t.key)}>
            <span className="ico">{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </nav>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}