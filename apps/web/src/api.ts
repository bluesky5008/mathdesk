export type CurrentUser = {
  id: number
  login_id: string
  display_name: string
  role: string
}

export type Student = {
  id: number
  name: string
  school: string | null
  grade: string | null
  phone: string | null
  status: string
  omr_number: string | null
}

export type Schedule = { weekday: number; start_time: string; end_time: string }

export type Klass = {
  id: number
  name: string
  grade: string | null
  teacher_id: number | null
  is_active: boolean
  schedules: Schedule[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: 'same-origin',
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? '요청을 처리하지 못했습니다.')
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  return request<CurrentUser>('/auth/me').catch(() => null)
}

export function login(loginId: string, password: string): Promise<CurrentUser> {
  return request<CurrentUser>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login_id: loginId, password }),
  })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST' })
}

export function fetchStudents(): Promise<Student[]> {
  return request<Student[]>('/students')
}

export function createStudent(payload: Partial<Student>): Promise<Student> {
  return request<Student>('/students', { method: 'POST', body: JSON.stringify(payload) })
}

export function fetchClasses(): Promise<Klass[]> {
  return request<Klass[]>('/classes')
}

export function createClass(payload: {
  name: string
  grade: string | null
  schedules: Schedule[]
}): Promise<Klass> {
  return request<Klass>('/classes', { method: 'POST', body: JSON.stringify(payload) })
}
