import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { documentsApi } from '../apis/documents'
import './DocumentViewer.css'

const DocumentViewer = ({ filename, onClose }) => {
  const [document, setDocument] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true)
        const data = await documentsApi.getDocument(filename)
        setDocument(data)
        setError(null)
      } catch (err) {
        setError('載入文件失敗: ' + err.message)
        console.error('Failed to load document:', err)
      } finally {
        setLoading(false)
      }
    }

    if (filename) {
      loadDocument()
    }
  }, [filename])

  const getStatusBadge = (status) => {
    const badges = {
      indexed: { label: '已索引', class: 'status-indexed' },
      modified: { label: '已修改', class: 'status-modified' },
      new: { label: '新文件', class: 'status-new' },
      deleted: { label: '已刪除', class: 'status-deleted' }
    }
    const badge = badges[status] || { label: status, class: 'status-unknown' }
    return <span className={`status-badge ${badge.class}`}>{badge.label}</span>
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="document-viewer-overlay">
        <div className="document-viewer-modal">
          <div className="document-viewer-loading">載入中...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="document-viewer-overlay">
        <div className="document-viewer-modal">
          <div className="document-viewer-error">{error}</div>
          <button className="btn-close" onClick={onClose}>關閉</button>
        </div>
      </div>
    )
  }

  if (!document) {
    return null
  }

  return (
    <div className="document-viewer-overlay" onClick={onClose}>
      <div className="document-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="document-viewer-header">
          <div className="document-info">
            <h2>{document.filename}</h2>
            <div className="document-meta">
              {getStatusBadge(document.status)}
              <span className="meta-item">索引時間: {formatDate(document.indexed_at)}</span>
              <span className="meta-item">更新時間: {formatDate(document.updated_at)}</span>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="document-viewer-content">
          <ReactMarkdown>{document.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

export default DocumentViewer
