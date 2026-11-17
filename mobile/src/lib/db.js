import { getSupabase } from './supabase'
import { normalizarNome } from './format'

function sb() {
  const c = getSupabase()
  if (!c) throw new Error('Supabase não configurado. Vá em Configurações.')
  return c
}

// ---------- CATÁLOGO ----------
export async function buscarCatalogo() {
  const { data, error } = await sb().from('catalogo').select('*').order('categoria').order('nome')
  if (error) throw error
  return (data || []).map(r => ({
    id: r.id,
    categoria: r.categoria || 'Geral',
    nome: r.nome,
    unidade: r.unidade || 'Unidade',
    preco: Number(r.preco) || 0,
    estoque: Number(r.estoque ?? r.estoque_total) || 0,
  }))
}

export async function salvarItemCatalogo(item) {
  const payload = {
    categoria: item.categoria || 'Geral',
    nome: item.nome,
    unidade: item.unidade || 'Unidade',
    preco: Number(item.preco) || 0,
    estoque: Number(item.estoque) || 0,
  }
  if (item.id) {
    const { error } = await sb().from('catalogo').update(payload).eq('id', item.id)
    if (error) throw error
  } else {
    const { error } = await sb().from('catalogo').insert(payload)
    if (error) throw error
  }
}

export async function excluirItemCatalogo(id) {
  const { error } = await sb().from('catalogo').delete().eq('id', id)
  if (error) throw error
}

// ---------- CLIENTES ----------
export async function buscarClientes(termo = '', limite = 50) {
  const { data, error } = await sb().from('clientes').select('*').order('nome')
  if (error) throw error
  let todos = data || []
  const t = (termo || '').trim()
  if (t) {
    const digitos = t.replace(/\D/g, '')
    const buscaTel = digitos.length >= 2 && digitos.length >= t.replace(/\s/g, '').length - 2
    const palavras = normalizarNome(t).split(' ')
    todos = todos.filter(r => {
      if (buscaTel) return digitos && (r.telefone || '').replace(/\D/g, '').includes(digitos)
      const nn = normalizarNome(r.nome)
      return palavras.every(p => nn.includes(p))
    })
  }
  return todos.slice(0, limite)
}

export async function listarClientes(filtro = '') {
  return buscarClientes(filtro, 10000)
}

export async function salvarCliente(cli) {
  // duplicata check
  const existentes = await buscarClientes('', 10000)
  const tel = (cli.telefone || '').replace(/\D/g, '')
  const nn = normalizarNome(cli.nome)
  const dup = existentes.find(r => {
    if (cli.id && r.id === cli.id) return false
    const rt = (r.telefone || '').replace(/\D/g, '')
    if (tel.length >= 8 && rt.length >= 8 && rt.slice(-8) === tel.slice(-8)) return true
    if (nn && normalizarNome(r.nome) === nn) return true
    return false
  })
  if (dup) {
    return { ok: false, msg: `Já existe um cliente cadastrado:\n${dup.nome} | ${dup.telefone || 'sem telefone'}` }
  }
  const payload = { nome: cli.nome, telefone: cli.telefone || '', endereco: cli.endereco || '' }
  if (cli.id) {
    const { error } = await sb().from('clientes').update(payload).eq('id', cli.id)
    if (error) return { ok: false, msg: error.message }
  } else {
    const { error } = await sb().from('clientes').insert(payload)
    if (error) return { ok: false, msg: error.message }
  }
  return { ok: true, msg: 'Cliente salvo com sucesso!' }
}

export async function excluirCliente(id) {
  const { error } = await sb().from('clientes').delete().eq('id', id)
  if (error) throw error
}

export async function encontrarClienteSimilar(nome, telefone) {
  const todos = await buscarClientes('', 10000)
  const tel = (telefone || '').replace(/\D/g, '')
  const nn = normalizarNome(nome)
  // telefone
  if (tel.length >= 8) {
    const achado = todos.find(r => {
      const rt = (r.telefone || '').replace(/\D/g, '')
      return rt.length >= 8 && rt.slice(-8) === tel.slice(-8)
    })
    if (achado) return achado
  }
  // nome
  if (nn) {
    const achado = todos.find(r => normalizarNome(r.nome) === nn)
    if (achado) return achado
  }
  // similaridade
  let melhor = null, score = 0
  for (const r of todos) {
    const s = similaridade(nn, normalizarNome(r.nome))
    if (s > score) { score = s; melhor = r }
  }
  if (score >= 0.85) return melhor
  return null
}

function similaridade(a, b) {
  // simple ratio
  if (!a || !b) return 0
  if (a === b) return 1
  const longer = a.length > b.length ? a : b
  const shorter = a.length > b.length ? b : a
  if (longer.length === 0) return 1
  return (longer.length - editDistance(longer, shorter)) / longer.length
}
function editDistance(a, b) {
  const m = a.length, n = b.length
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = 0; i <= m; i++) dp[i][0] = i
  for (let j = 0; j <= n; j++) dp[0][j] = j
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
  return dp[m][n]
}

// ---------- PEDIDOS / ORÇAMENTOS ----------
export async function buscarPorStatus(status) {
  let q = sb().from('orcamentos').select('*').order('id', { ascending: false })
  if (status === 'Pedido') {
    q = q.in('tipo', ['Pedido', 'Ja Entregue', 'Ja Recolhido', 'Arquivado'])
  } else {
    q = q.eq('tipo', status)
  }
  const { data, error } = await q
  if (error) throw error
  return (data || []).map(r => ({
    id: r.id,
    cliente: r.cliente,
    telefone: r.telefone,
    endereco: r.endereco,
    data_evento: r.data_evento,
    tipo: r.tipo,
  }))
}

export async function buscarTodosPedidosRelatorio() {
  const { data, error } = await sb().from('orcamentos').select('*')
  if (error) throw error
  return (data || []).map(r => ({
    id: r.id,
    cliente: r.cliente,
    telefone: r.telefone,
    endereco: r.endereco,
    data_evento: r.data_evento,
    orcamento: r.orcamento,
    tipo: r.tipo,
    distancia_km: Number(r.distancia_km) || 0,
    desconto: Number(r.desconto) || 0,
    observacoes: r.observacoes || '',
    criado_em: r.criado_em,
  }))
}

export async function buscarPorId(id) {
  const { data, error } = await sb().from('orcamentos').select('*').eq('id', id).single()
  if (error) return null
  const r = data
  return {
    id: r.id,
    cliente: r.cliente,
    telefone: r.telefone,
    endereco: r.endereco,
    data_evento: r.data_evento,
    orcamento: r.orcamento,
    tipo: r.tipo,
    distancia_km: Number(r.distancia_km) || 0,
    desconto: Number(r.desconto) || 0,
    observacoes: r.observacoes || '',
  }
}

export async function inserirPedido(dados, tipo = 'Orcamento') {
  const payload = {
    cliente: dados.cliente || '',
    telefone: dados.telefone || '',
    endereco: dados.endereco || '',
    data_evento: dados.data_evento || '',
    orcamento: dados.orcamento || '',
    tipo,
    distancia_km: Number(dados.distancia_km) || 0,
    desconto: Number(dados.desconto) || 0,
    observacoes: dados.observacoes || '',
  }
  const { data, error } = await sb().from('orcamentos').insert(payload).select().single()
  if (error) throw error
  // registrar cliente
  try { await registrarClienteAuto(dados.cliente, dados.telefone, dados.endereco) } catch (e) {}
  return data.id
}

export async function atualizarPedido(id, dados) {
  const payload = {
    cliente: dados.cliente || '',
    telefone: dados.telefone || '',
    endereco: dados.endereco || '',
    data_evento: dados.data_evento || '',
    orcamento: dados.orcamento || '',
    distancia_km: Number(dados.distancia_km) || 0,
    desconto: Number(dados.desconto) || 0,
    observacoes: dados.observacoes || '',
  }
  const { error } = await sb().from('orcamentos').update(payload).eq('id', id)
  if (error) throw error
  try { await registrarClienteAuto(dados.cliente, dados.telefone, dados.endereco) } catch (e) {}
}

export async function alterarStatus(id, novoStatus) {
  const { error } = await sb().from('orcamentos').update({ tipo: novoStatus }).eq('id', id)
  if (error) throw error
}

export async function alterarStatusMultiplos(ids, novoStatus) {
  if (!ids || !ids.length) return
  const { error } = await sb().from('orcamentos').update({ tipo: novoStatus }).in('id', ids)
  if (error) throw error
}

async function registrarClienteAuto(nome, telefone, endereco) {
  const todos = await buscarClientes('', 10000)
  const tel = (telefone || '').replace(/\D/g, '')
  const nn = normalizarNome(nome)
  const achado = todos.find(r => {
    const rt = (r.telefone || '').replace(/\D/g, '')
    if (tel.length >= 8 && rt.length >= 8 && rt.slice(-8) === tel.slice(-8)) return true
    if (nn && normalizarNome(r.nome) === nn) return true
    return false
  })
  if (achado) return achado.id
  if (!nome) return null
  const { data } = await sb().from('clientes').insert({ nome, telefone: telefone || '', endereco: endereco || '' }).select().single()
  return data?.id
}