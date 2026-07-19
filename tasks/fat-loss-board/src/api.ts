import type { StatusResponse } from './lib/types'

export async function fetchStatus(signal?: AbortSignal): Promise<StatusResponse> {
  const res = await fetch('/api/status', { signal })
  if (!res.ok) throw new Error(`status ${res.status}`)
  return res.json() as Promise<StatusResponse>
}
