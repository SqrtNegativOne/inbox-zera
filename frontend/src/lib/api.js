/**
 * Thin API client. All fetch calls live here — components never call fetch directly.
 */

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export async function fetchAccounts() {
  return request('/accounts')
}

export async function fetchLabels() {
  return request('/labels')
}

export async function fetchNextEmail() {
  return request('/emails/next')
}

export async function classifyEmail(emailId, labelId, account) {
  return request(`/emails/${emailId}/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label_id: labelId, account }),
  })
}
