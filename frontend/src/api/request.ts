/**
 * Shared fetch helper. Every API hook goes through this.
 *
 * credentials: 'include' is mandatory — auth is an HttpOnly session cookie, which JS
 * cannot read or attach manually.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  // Declared and assigned explicitly: parameter properties are TS-only syntax, which
  // `erasableSyntaxOnly` (on in this project) forbids.
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }

  /** 401 means "not logged in" — the router guard treats this specially. */
  get isUnauthorized() {
    return this.status === 401
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE'

export async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server')
  }

  if (!response.ok) {
    // FastAPI returns { detail: ... }; fall back to the status text when it doesn't.
    let detail = response.statusText
    try {
      const payload = await response.json()
      if (typeof payload?.detail === 'string') detail = payload.detail
    } catch {
      /* body wasn't JSON — keep statusText */
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Full-page navigation, not fetch: the OAuth flow redirects away to Strava. */
export function navigateTo(path: string) {
  window.location.href = `${BASE_URL}${path}`
}
