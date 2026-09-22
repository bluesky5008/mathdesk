export type CurrentUser = {
  id: number
  login_id: string
  display_name: string
  role: string
}

async function request(path: string, init?: RequestInit) {
  return fetch(`/api${path}`, { credentials: 'same-origin', ...init })
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await request('/auth/me')
  return response.ok ? ((await response.json()) as CurrentUser) : null
}

export async function login(loginId: string, password: string): Promise<CurrentUser> {
  const response = await request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login_id: loginId, password }),
  })
  if (!response.ok) {
    throw new Error('아이디 또는 비밀번호가 올바르지 않습니다.')
  }
  return (await response.json()) as CurrentUser
}

export async function logout(): Promise<void> {
  await request('/auth/logout', { method: 'POST' })
}
