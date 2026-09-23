export type CurrentUser = {
  id: number
  login_id: string
  display_name: string
  role: string
}

export type Brand = {
  campus_name: string
  brand_colour: string | null
  logo_data_url: string | null
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

export function updateStudent(id: number, payload: Partial<Student>): Promise<Student> {
  return request<Student>(`/students/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function fetchClasses(includeInactive = false): Promise<Klass[]> {
  return request<Klass[]>(`/classes${includeInactive ? '?include_inactive=true' : ''}`)
}

export type ClassPayload = {
  name: string
  grade: string | null
  teacher_id?: number | null
  is_active?: boolean
  schedules: Schedule[]
}

export function createClass(payload: ClassPayload): Promise<Klass> {
  return request<Klass>('/classes', { method: 'POST', body: JSON.stringify(payload) })
}

export type Enrollment = {
  id: number
  student_id: number
  start_date: string
  end_date: string | null
}

export function fetchEnrollments(classId: number, on?: string): Promise<Enrollment[]> {
  return request<Enrollment[]>(`/classes/${classId}/enrollments${on ? `?on=${on}` : ''}`)
}

export function createEnrollment(
  classId: number,
  studentId: number,
  startDate: string,
): Promise<Enrollment> {
  return request<Enrollment>(`/classes/${classId}/enrollments`, {
    method: 'POST',
    body: JSON.stringify({ student_id: studentId, start_date: startDate }),
  })
}

/** 해제는 삭제가 아니라 배정 기간의 종료다. 과거 수업일의 명단이 유지된다. */
export function endEnrollment(
  classId: number,
  enrollmentId: number,
  endDate: string,
): Promise<Enrollment> {
  return request<Enrollment>(`/classes/${classId}/enrollments/${enrollmentId}`, {
    method: 'PATCH',
    body: JSON.stringify({ end_date: endDate }),
  })
}

export function updateClass(id: number, payload: ClassPayload): Promise<Klass> {
  return request<Klass>(`/classes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
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

export type Dashboard = {
  campus: { enrolled_students: number; active_classes: number }
  attendance: {
    class_id: number
    class_name: string
    enrolled: number
    attending: number
  } | null
  homework: {
    completion_rate: number | null
    delta_points: number | null
    missing: number
    recheck_targets: number
  }
  test: {
    average: number | null
    count: number
    max: number | null
    max_count: number
    min: number | null
  }
  last_session: {
    session_date: string
    progress: { period: number; content: string | null }[]
    homework: string | null
  } | null
}

export function fetchDashboard(classId: number, date: string): Promise<Dashboard> {
  return request<Dashboard>(`/dashboard?class_id=${classId}&date=${date}`)
}

export type SendResult = {
  recipient_phone: string
  recipient_type: string
  status: string
  result_code: string | null
  error: string | null
}

export type MessageLog = {
  id: number
  student_id: number | null
  recipient_type: string
  recipient_phone: string
  channel: string
  status: string
  body_snapshot: string
  is_test: boolean
  requested_at: string
  result_code: string | null
  error: string | null
}

export function fetchMessagePreview(sessionId: number, studentId: number): Promise<{ body: string }> {
  return request<{ body: string }>(
    `/messages/preview?session_id=${sessionId}&student_id=${studentId}`,
  )
}

export function reportImageUrl(sessionId: number, studentId: number): string {
  return `/api/messages/report-image?session_id=${sessionId}&student_id=${studentId}`
}

export function sendMessage(
  sessionId: number,
  studentId: number,
  recipients: string[],
): Promise<{ channel: string; results: SendResult[] }> {
  return request<{ channel: string; results: SendResult[] }>('/messages/send', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, student_id: studentId, recipients }),
  })
}

export function fetchMessageLogs(): Promise<MessageLog[]> {
  return request<MessageLog[]>('/messages/logs')
}

export function fetchBrand(): Promise<Brand> {
  return request<Brand>('/settings/brand')
}

export function saveBrand(payload: Brand): Promise<Brand> {
  return request<Brand>('/settings/brand', { method: 'PUT', body: JSON.stringify(payload) })
}

export type StudentWeek = {
  week_start: string
  test_average: number | null
  class_test_average: number | null
  homework_grades: string[]
  homework_completion: number | null
  class_homework_completion: number | null
  attendance_rate: number | null
}

export type StudentHistory = {
  student: { id: number; name: string }
  klass: { id: number; name: string } | null
  weeks: StudentWeek[]
}

export type StudentStatRow = {
  student_id: number
  name: string
  test_average: number | null
  homework_completion: number | null
  attendance_rate: number | null
}

export type PeriodStats = {
  start: string
  end: string
  students: StudentStatRow[]
  test: { average: number | null; count: number; distribution: { bucket: string; count: number }[] }
  homework: { completion_rate: number | null; distribution: Record<string, number> }
  attendance_rate: number | null
}

export type ClassStats = {
  klass: { id: number; name: string }
  period: PeriodStats
  compare: PeriodStats | null
}

export function fetchClassStats(classId: number, start: string, end: string): Promise<ClassStats> {
  return request<ClassStats>(`/stats/classes/${classId}?start=${start}&end=${end}`)
}

export function fetchStudentHistory(
  studentId: number,
  to: string,
  classId: number,
): Promise<StudentHistory> {
  return request<StudentHistory>(
    `/stats/students/${studentId}?to=${to}&weeks=8&class_id=${classId}`,
  )
}

/** 내려받기는 브라우저가 직접 받아야 하므로 fetch가 아니라 링크 주소를 준다. */
export function statsExportUrl(classId: number, start: string, end: string): string {
  return `/api/stats/export?class_id=${classId}&start=${start}&end=${end}`
}
