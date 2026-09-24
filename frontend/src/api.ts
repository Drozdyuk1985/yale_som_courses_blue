// In production Render injects VITE_API_URL at build time; locally we hit the dev backend.
const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const TOKEN_KEY = 'som_token'
const USER_KEY = 'som_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getUsername(): string | null {
  return localStorage.getItem(USER_KEY)
}

export function saveSession(token: string, username: string) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, username)
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function unwrap(response: Response) {
  if (response.status === 401) {
    clearSession()
    throw new Error('Your session expired. Please sign in again.')
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return response.json()
}

// Rows come from the courses table, so keys are snake_case.
export type Course = {
  course_id: string
  course_number: string
  course_title: string
  course_category: string
  course_type: string
  section: string
  faculty: string
  faculty_email: string
  daytimes: string
  room: string
  units: string
  bid_or_permission: string
  course_description: string
  faculty_bio: string
  syllabus: string
  visible: string
}

export type CoursesResponse = { count: number; courses: Course[] }
export type ChatResponse = { reply: string; tools_used: string[] }
export type AuthResponse = { token: string; username: string }
export type ChatMessageRow = {
  id: number
  role: 'user' | 'agent'
  content: string
  tools_used: string[]
  created_at: string | null
}

export async function fetchCourses(q?: string): Promise<CoursesResponse> {
  const url = q ? `${BASE}/api/courses?q=${encodeURIComponent(q)}` : `${BASE}/api/courses`
  return unwrap(await fetch(url))
}

export async function register(username: string, password: string): Promise<AuthResponse> {
  return unwrap(await fetch(`${BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }))
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  return unwrap(await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }))
}

export async function fetchHistory(): Promise<{ messages: ChatMessageRow[] }> {
  return unwrap(await fetch(`${BASE}/api/chat/history`, { headers: authHeaders() }))
}

export async function sendChat(message: string): Promise<ChatResponse> {
  return unwrap(await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message }),
  }))
}

export async function clearHistory(): Promise<{ deleted: number }> {
  return unwrap(await fetch(`${BASE}/api/chat/history`, {
    method: 'DELETE',
    headers: authHeaders(),
  }))
}
