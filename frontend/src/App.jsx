import { useState, useCallback } from 'react'
import UploadZone from './components/UploadZone'
import ChatWindow from './components/ChatWindow'

const BASE = "https://docmind-pdf-q-a-chatbot-production.up.railway.app"


export default function App() {
  const [docInfo, setDocInfo] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [toasts, setToasts] = useState([])

  const showToast = useCallback((message) => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }, [])

  const handleUploadSuccess = useCallback((filename, chunkCount) => {
    setDocInfo({ filename, chunkCount })
    setMessages([])
  }, [])

  const handleSendMessage = useCallback(async (question) => {
    if (!question.trim() || isLoading) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: question.trim(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    try {
      const res = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }
      const data = await res.json()
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }])
    } catch (err) {
      showToast(err.message || 'Failed to get a response. Is the backend running?')
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, showToast])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">📄</div>
            <span className="sidebar-logo-text">DocMind</span>
          </div>
          <p className="sidebar-tagline">AI-powered PDF analysis</p>
        </div>

        <div className="sidebar-body">
          <div>
            <p className="sidebar-section-title">Document</p>
            <UploadZone onSuccess={handleUploadSuccess} onError={showToast} />
          </div>

          {docInfo && (
            <div>
              <p className="sidebar-section-title">Document Info</p>
              <div style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>FILE</span>
                  <div style={{ color: 'var(--text-primary)', fontWeight: 500, marginTop: 2, wordBreak: 'break-all' }}>
                    {docInfo.filename}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginTop: 4 }}>
                  <span className="upload-meta-dot" />
                  <span style={{ fontSize: 12, color: 'var(--accent)' }}>
                    {docInfo.chunkCount} chunks indexed
                  </span>
                </div>
              </div>
            </div>
          )}

          <div style={{ marginTop: 'auto' }}>
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              fontSize: 12,
              color: 'var(--text-muted)',
              lineHeight: 1.7,
            }}>
              <div style={{ color: 'var(--text-secondary)', fontWeight: 500, marginBottom: 4 }}>
                How it works
              </div>
              Answers are retrieved directly from the uploaded document using semantic search. No external knowledge is used.
            </div>
          </div>
        </div>
      </aside>

      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        docReady={!!docInfo}
        onSend={handleSendMessage}
      />

      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className="toast">{t.message}</div>
        ))}
      </div>
    </div>
  )
}
