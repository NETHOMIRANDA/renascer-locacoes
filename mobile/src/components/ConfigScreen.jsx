import React, { useState } from 'react'
import { loadConfig, saveConfig } from '../lib/store'
import { resetSupabase } from '../lib/supabase'

export default function ConfigScreen({ onDone, showToast }) {
  const cfg = loadConfig()
  const [url, setUrl] = useState(cfg.url || '')
  const [key, setKey] = useState(cfg.key || '')

  function salvar() {
    if (!url.trim() || !key.trim()) {
      showToast?.('Preencha URL e chave')
      return
    }
    saveConfig({ url: url.trim(), key: key.trim() })
    resetSupabase()
    showToast?.('Configuração salva')
    onDone()
  }

  return (
    <div className="app">
      <div className="header"><div>Configurações</div></div>
      <div className="content">
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Conexão Supabase</h3>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
            Informe a URL do projeto e a service_role key do Supabase (mesmas do sistema desktop).
          </p>
          <div className="field">
            <label className="label">SUPABASE_URL</label>
            <input className="input" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://xxx.supabase.co" />
          </div>
          <div className="field">
            <label className="label">SUPABASE_KEY (service_role)</label>
            <input className="input" type="password" value={key} onChange={e => setKey(e.target.value)} placeholder="eyJ..." />
          </div>
          <button className="btn" onClick={salvar}>Salvar e entrar</button>
        </div>
      </div>
    </div>
  )
}