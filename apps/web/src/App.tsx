import { useEffect, useState } from 'react'

export function App() {
  const [apiStatus, setApiStatus] = useState('확인 중')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => response.json())
      .then((body: { status: string }) => setApiStatus(body.status))
      .catch(() => setApiStatus('연결 실패'))
  }, [])

  return (
    <main>
      <h1>mathdesk</h1>
      <p>API 상태: {apiStatus}</p>
    </main>
  )
}
