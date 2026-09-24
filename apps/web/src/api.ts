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

export function fetchMessagePreview(
  sessionId: number,
  studentId: number,
  templateCode?: string,
): Promise<{ body: string }> {
  const template = templateCode ? `&template_code=${encodeURIComponent(templateCode)}` : ''
  return request<{ body: string }>(
    `/messages/preview?session_id=${sessionId}&student_id=${studentId}${template}`,
  )
}

export function reportImageUrl(sessionId: number, studentId: number): string {
  return `/api/messages/report-image?session_id=${sessionId}&student_id=${studentId}`
}

export function sendMessage(
  sessionId: number,
  studentId: number,
  recipients: string[],
  templateCode?: string,
): Promise<{ channel: string; results: SendResult[] }> {
  // 템플릿 코드가 있으면 알림톡, 없으면 문자다(키 자체를 보내지 않는다)
  const body = { session_id: sessionId, student_id: studentId, recipients }
  return request<{ channel: string; results: SendResult[] }>('/messages/send', {
    method: 'POST',
    body: JSON.stringify(templateCode ? { ...body, template_code: templateCode } : body),
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

export type ExamRow = {
  id: number
  name: string
  source_file_id: number | null
  class_id: number | null
  exam_date: string | null
  question_count: number | null
  status: string
  needs_review: number
}

export type Difficulty = 'low' | 'mid' | 'high' | 'top'

export type ExamDetail = Omit<ExamRow, 'needs_review'> & {
  max_score: number | null
  answer_key_odd: (number | null)[] | null
  answer_key_even: (number | null)[] | null
  difficulty: Record<Difficulty, number>
}

export type ExamQuestion = {
  no: number
  unit: string | null
  sub_type: string | null
  difficulty: string | null
  rationale: string | null
  points: number | null
  confidence: number | null
  needs_review: boolean
}

export type ExamPatch = Partial<{
  name: string
  question_count: number
  max_score: number
  answer_key_odd: (number | null)[]
  answer_key_even: (number | null)[]
  status: 'draft' | 'confirmed'
}>

export type QuestionPatch = { no: number } & Partial<
  Pick<ExamQuestion, 'unit' | 'sub_type' | 'difficulty' | 'rationale' | 'points'>
>

export type Task = {
  id: number
  kind: string
  status: string
  progress: number
  result: Record<string, unknown> | null
  error: string | null
}

export function fetchExams(): Promise<ExamRow[]> {
  return request<ExamRow[]>('/exams')
}

export function fetchExam(id: number): Promise<ExamDetail> {
  return request<ExamDetail>(`/exams/${id}`)
}

export function fetchQuestions(id: number): Promise<ExamQuestion[]> {
  return request<ExamQuestion[]>(`/exams/${id}/questions`)
}

export function updateExam(id: number, payload: ExamPatch): Promise<ExamDetail> {
  return request<ExamDetail>(`/exams/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function updateQuestions(id: number, questions: QuestionPatch[]): Promise<ExamQuestion[]> {
  return request<ExamQuestion[]>(`/exams/${id}/questions`, {
    method: 'PATCH',
    body: JSON.stringify({ questions }),
  })
}

/** 파일 업로드 → 시험 등록 → 분석 시작. 분석은 배경 작업이라 task_id만 돌려준다. */
export async function registerExam(name: string, file: File): Promise<{ examId: number; taskId: number }> {
  const form = new FormData()
  form.append('file', file)
  // multipart 경계는 브라우저가 정한다. request()처럼 JSON Content-Type을 붙이면 안 된다
  const uploaded = await fetch('/api/exams/uploads', {
    method: 'POST',
    credentials: 'same-origin',
    body: form,
  })
  if (!uploaded.ok) {
    const body = (await uploaded.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? '파일을 올리지 못했습니다.')
  }
  const stored = (await uploaded.json()) as { id: number }
  const exam = await request<ExamRow>('/exams', {
    method: 'POST',
    body: JSON.stringify({ name, source_file_id: stored.id }),
  })
  const task = await request<{ task_id: number }>(`/exams/${exam.id}/analyze`, { method: 'POST' })
  return { examId: exam.id, taskId: task.task_id }
}

export function fetchTask(id: number): Promise<Task> {
  return request<Task>(`/tasks/${id}`)
}

export function difficultyCardUrl(examId: number): string {
  return `/api/exams/${examId}/difficulty-card`
}

export type OmrFlag = { field: string; code: 'blank' | 'multi' | 'low_confidence' | 'unmatched' }

export type OmrScan = {
  id: number
  file_id: number | null
  page_no: number
  status: 'read' | 'needs_review' | 'applied'
  student: { id: number; name: string } | null
  exam_number: string | null
  form: 'odd' | 'even' | null
  answers: Record<string, number | null>
  flags: OmrFlag[]
  error: string | null
}

export type OmrScanPatch = {
  student_id?: number
  exam_number?: string
  form?: 'odd' | 'even'
  answers?: Record<string, number | null>
}

export function fetchOmrScans(examId: number): Promise<OmrScan[]> {
  return request<OmrScan[]>(`/exams/${examId}/omr/scans`)
}

export function updateOmrScan(examId: number, scanId: number, patch: OmrScanPatch): Promise<OmrScan> {
  return request<OmrScan>(`/exams/${examId}/omr/scans/${scanId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}

export function omrImageUrl(examId: number, scanId: number, field?: string): string {
  const base = `/api/exams/${examId}/omr/scans/${scanId}/image`
  return field ? `${base}?field=${field}` : base
}

export async function uploadOmr(examId: number, file: File): Promise<{ file_id: number; task_id: number }> {
  const form = new FormData()
  form.append('file', file)
  // multipart 경계는 브라우저가 정한다(registerExam과 같은 이유로 fetch를 직접 쓴다)
  const response = await fetch(`/api/exams/${examId}/omr/uploads`, {
    method: 'POST',
    credentials: 'same-origin',
    body: form,
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? '파일을 올리지 못했습니다.')
  }
  return (await response.json()) as { file_id: number; task_id: number }
}

export type OmrApplyResult = {
  applied: number
  replaced: number
  removed: number
  waiting: number
  conflicts: { student: { id: number; name: string }; pages: number[] }[]
}

export function applyOmr(examId: number): Promise<OmrApplyResult> {
  return request<OmrApplyResult>(`/exams/${examId}/omr/apply`, { method: 'POST' })
}

export type ExamResults = {
  score_basis: 'points' | 'ratio'
  summary: {
    attempts: number
    enrolled: number | null
    average: number | null
    highest: number | null
    lowest: number | null
    average_correct_rate: number | null
    focus_questions: number[]
  }
  students: {
    student: { id: number; name: string }
    form: 'odd' | 'even' | null
    source: 'omr' | 'manual'
    score: number | null
    correct: number
    answers: { no: number; value: string | null; correct: boolean | null }[]
  }[]
}

export type QuestionStats = {
  questions: {
    no: number
    answer: number | null
    answer_even: number | null
    correct_rate: number | null
    choices: Record<string, number>
    unit: string | null
    sub_type: string | null
    difficulty: Difficulty | null
  }[]
  units: { unit: string; questions: number; wrong_rate: number | null }[]
}

export function fetchExamResults(examId: number): Promise<ExamResults> {
  return request<ExamResults>(`/exams/${examId}/results`)
}

export function fetchQuestionStats(examId: number): Promise<QuestionStats> {
  return request<QuestionStats>(`/exams/${examId}/question-stats`)
}

export type Consult = {
  id: number
  student_id: number
  consulted_on: string
  content: string
  follow_up: string | null
  author: { id: number; name: string } | null
}

export type ConsultInput = { consulted_on: string; content: string; follow_up: string | null }

export function fetchConsults(studentId: number): Promise<Consult[]> {
  return request<Consult[]>(`/students/${studentId}/consults`)
}

export function createConsult(studentId: number, input: ConsultInput): Promise<Consult> {
  return request<Consult>(`/students/${studentId}/consults`, { method: 'POST', body: JSON.stringify(input) })
}

export function updateConsult(studentId: number, consultId: number, input: ConsultInput): Promise<Consult> {
  return request<Consult>(`/students/${studentId}/consults/${consultId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export type AlimtalkTemplate = { code: string; body: string; variables: Record<string, string> }

export type AlimtalkSettings = {
  fallback_to_sms: boolean
  alimtalk: AlimtalkTemplate[]
  fields: { key: string; label: string }[]
}

export function fetchAlimtalkSettings(): Promise<AlimtalkSettings> {
  return request<AlimtalkSettings>('/messages/templates')
}

export function saveAlimtalkSettings(settings: {
  fallback_to_sms: boolean
  alimtalk: AlimtalkTemplate[]
}): Promise<AlimtalkSettings> {
  return request<AlimtalkSettings>('/messages/templates', { method: 'PUT', body: JSON.stringify(settings) })
}
