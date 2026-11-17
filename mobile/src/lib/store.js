const KEY = 'renascer_config_v1'

export function loadConfig() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {}
  return { url: '', key: '' }
}

export function saveConfig(cfg) {
  localStorage.setItem(KEY, JSON.stringify(cfg))
}

export function isConfigured() {
  const c = loadConfig()
  return !!(c.url && c.key)
}