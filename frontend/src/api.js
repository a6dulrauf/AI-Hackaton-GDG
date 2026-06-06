// Thin fetch wrappers around the backend. Throws on non-2xx so callers can catch.
import { API_BASE } from './config'

async function post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data.detail) detail = data.detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const parseRequest = (text) => post('/request/parse', { text })
export const createRequest = (body) => post('/request/create', body)
export const getStatus = (id) => get(`/request/${id}/status`)
export const escalateRequest = (id) => post(`/request/${id}/escalate`, {})
export const respondDonor = (body) => post('/donor/respond', body)

export async function transcribeVoice(blob) {
  const fd = new FormData()
  fd.append('file', blob, 'voice.webm')
  const res = await fetch(`${API_BASE}/voice`, { method: 'POST', body: fd })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try { const d = await res.json(); if (d.detail) detail = d.detail } catch { /* */ }
    throw new Error(detail)
  }
  return res.json() // { text }
}
