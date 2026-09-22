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

export type Recheck = {
  target: boolean
  prev_grade: string | null
  prev_date: string | null
  result: string | null
}

export type DailyRecord = {
  student_id: number
  name: string
  attendance_status: string
  attendance_reason: string | null
  homework_grade: string | null
  recheck: Recheck
  test_score_num: string | number | null
  test_score_text: string | null
}

export type DailySession = {
  id: number
  class_id: number
  session_date: string
  progress: { period: number; content: string | null }[]
  homework: string | null
  video_url: string | null
  teacher_note: string | null
  test_name: string | null
  test_max_score: number | null
  attendance_confirmed_at: string | null
}

export type Daily = {
  session: DailySession
  records: DailyRecord[]
  summary: { enrolled: number; attending: number; test_average: number | null; test_count: number }
}

export type RecordPatch = {
  student_id: number
  attendance_status?: string
  attendance_reason?: string | null
  homework_grade?: string | null
  test_score_num?: number | null
}

export type NotesPatch = Partial<{
  progress: { period: number; content: string | null }[]
  homework: string | null
  video_url: string | null
  teacher_note: string | null
  test_name: string | null
  test_max_score: number | null
}>

export function fetchDaily(classId: number, date: string): Promise<Daily> {
  return request<Daily>(`/daily?class_id=${classId}&date=${date}`)
}

export function saveDailyRecords(sessionId: number, records: RecordPatch[]): Promise<Daily> {
  return request<Daily>(`/daily/${sessionId}/records`, {
    method: 'PUT',
    body: JSON.stringify({ records }),
  })
}

export function saveDailyNotes(sessionId: number, notes: NotesPatch): Promise<Daily> {
  return request<Daily>(`/daily/${sessionId}/notes`, {
    method: 'PUT',
    body: JSON.stringify(notes),
  })
}

export function saveRecheck(
  sessionId: number,
  studentId: number,
  result: string | null,
): Promise<Daily> {
  return request<Daily>(`/daily/${sessionId}/records/${studentId}/recheck`, {
    method: 'PUT',
    body: JSON.stringify({ result }),
  })
}

export function setAttendanceConfirmed(sessionId: number, confirmed: boolean): Promise<Daily> {
  return request<Daily>(`/daily/${sessionId}/attendance/${confirmed ? 'confirm' : 'unlock'}`, {
    method: 'POST',
  })
}
