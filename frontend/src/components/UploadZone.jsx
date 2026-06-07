import { useState, useRef, useCallback } from 'react'

const BASE = 'https://docmind-pdf-q-a-chatbot-production.up.railway.app'

export default function UploadZone({ onSuccess, onError }) {
  const [state, setState] = useState('idle')
  const [fileInfo, setFileInfo] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef(null)

  const uploadFile = useCallback(async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      onError('Only PDF files are supported.')
      return
    }

    setState('uploading')
    const fd = new FormData()
    fd.append('file', file)

    try {
      const res = await fetch(`${BASE}/upload`, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Upload failed (${res.status})`)
      }
      const data = await res.json()
      setFileInfo({ filename: file.name, chunkCount: data.chunk_count })
      setState('done')
      onSuccess(file.name, data.chunk_count)
    } catch (err) {
      setState('idle')
      onError(err.message || 'Upload failed. Is the backend running?')
    }
  }, [onSuccess, onError])

  const onDragOver = (e) => { e.preventDefault(); setDragActive(true) }
  const onDragLeave = () => setDragActive(false)
  const onDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file) uploadFile(file)
  }
  const onInputChange = (e) => {
    const file = e.target.files[0]
    if (file) uploadFile(file)
    e.target.value = ''
  }

  const reset = () => {
    setState('idle')
    setFileInfo(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  if (state === 'uploading') {
    return (
      <div className="upload-loading">
        <div className="upload-loading-spinner" />
        <p className="upload-loading-text">Processing PDF…</p>
      </div>
    )
  }

  if (state === 'done' && fileInfo) {
    return (
      <div className="upload-success">
        <div className="upload-success-header">
          <div className="upload-check-icon">
            <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="2 6 5 9 10 3" />
            </svg>
          </div>
          <span className="upload-filename" title={fileInfo.filename}>
            {fileInfo.filename}
          </span>
        </div>
        <div className="upload-meta">
          <span className="upload-meta-dot" />
          <span>{fileInfo.chunkCount} chunks ready</span>
          <span style={{ marginLeft: 'auto', color: 'var(--accent)', fontWeight: 500 }}>✓ Indexed</span>
        </div>
        <button className="upload-change-btn" onClick={reset}>
          ↺ Upload different document
        </button>
      </div>
    )
  }

  return (
    <div
      className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-label="Upload PDF"
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf" onChange={onInputChange} tabIndex={-1} />
      <svg className="upload-icon" viewBox="0 0 44 44" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 4h18l8 8v24a3 3 0 01-3 3H9a3 3 0 01-3-3V7a3 3 0 013-3z" />
        <path d="M24 4v8h8" />
        <path d="M16 22l4-4 4 4" />
        <line x1="20" y1="18" x2="20" y2="28" />
      </svg>
      <p className="upload-primary-text">Drop your <span className="upload-accent">PDF</span> here</p>
      <p className="upload-secondary-text">or click to browse</p>
    </div>
  )
}
