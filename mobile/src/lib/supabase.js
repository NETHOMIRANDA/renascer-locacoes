import { createClient } from '@supabase/supabase-js'
import { loadConfig } from './store'

let client = null
let cachedKey = ''

export function getSupabase() {
  const cfg = loadConfig()
  const signature = cfg.url + '|' + cfg.key
  if (client && signature === cachedKey) return client
  if (!cfg.url || !cfg.key) return null
  client = createClient(cfg.url, cfg.key, { auth: { persistSession: false } })
  cachedKey = signature
  return client
}

export function resetSupabase() {
  client = null
  cachedKey = ''
}