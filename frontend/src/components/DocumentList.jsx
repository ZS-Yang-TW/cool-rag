import { useEffect, useState } from 'react'
import { documentsApi } from '../apis/documents'
import './DocumentList.css'

const DocumentList = ({ onSelectDocument }) => {
  const [documents, setDocuments] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFiles, setSelectedFiles] = useState(new Set())
  const [statusFilter, setStatusFilter] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [reindexing, setReindexing] = useState(false)
  const [initialSyncDone, setInitialSyncDone] = useState(false)

  const loadDocuments = async (filter = null) => {
    try {
      setLoading(true)
      const data = await documentsApi.getDocuments(filter)
      setDocuments(data.documents)
      setStats(data.stats)
      setError(null)
    } catch (err) {
      setError('載入文件列表失敗: ' + err.message)
      console.error('Failed to load documents:', err)
    } finally {
      setLoading(false)
    }
  }

  const syncDocuments = async () => {
    try {
      setSyncing(true)
      // Sync documents in backend
      await documentsApi.syncDocuments()
      
      // Reload documents with current filter
      // This will also refresh the stats
      await loadDocuments(statusFilter)
      
      setError(null)
    } catch (err) {
      setError('同步失敗: ' + err.message)
      console.error('Failed to sync documents:', err)
    } finally {
      setSyncing(false)
    }
  }

  // Initial load with auto-sync
  useEffect(() => {
    const initialize = async () => {
      await syncDocuments() // Auto-sync on initial load
      setInitialSyncDone(true)
    }
    initialize()
  }, [])

  // Reload when filter changes (after initial sync)
  useEffect(() => {
    if (initialSyncDone) {
      loadDocuments(statusFilter)
    }
  }, [statusFilter, initialSyncDone])

  const handleSync = async () => {
    await syncDocuments()
  }

  const handleReindex = async () => {
    if (selectedFiles.size === 0) {
      alert('請選擇要重新索引的文件')
      return
    }

    if (!confirm(`確定要重新索引 ${selectedFiles.size} 個文件嗎？`)) {
      return
    }

    try {
      setReindexing(true)
      const filenames = Array.from(selectedFiles)
      const result = await documentsApi.reindexDocuments(filenames)
      
      alert(`${result.message}\n成功: ${result.reindexed_count}\n失敗: ${result.failed_count}`)
      
      // Reload documents and clear selection
      await loadDocuments(statusFilter)
      setSelectedFiles(new Set())
      setError(null)
    } catch (err) {
      setError('重新索引失敗: ' + err.message)
      console.error('Failed to reindex documents:', err)
    } finally {
      setReindexing(false)
    }
  }

  const handleCleanup = async () => {
    const deletedCount = stats.deleted || 0
    
    if (deletedCount === 0) {
      alert('沒有需要清理的已刪除文件')
      return
    }

    if (!confirm(`確定要清理 ${deletedCount} 個已刪除的文件嗎？\n這將永久刪除它們的索引和資料庫記錄。`)) {
      return
    }

    try {
      setLoading(true)
      const result = await documentsApi.cleanupDeletedDocuments()
      alert(result.message)
      
      // Reload documents
      await loadDocuments(statusFilter)
      setError(null)
    } catch (err) {
      setError('清理失敗: ' + err.message)
      console.error('Failed to cleanup documents:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectAll = (checked) => {
    if (checked) {
      const allFiles = new Set(documents.map(doc => doc.filename))
      setSelectedFiles(allFiles)
    } else {
      setSelectedFiles(new Set())
    }
  }

  const handleSelectFile = (filename, checked) => {
    const newSelected = new Set(selectedFiles)
    if (checked) {
      newSelected.add(filename)
    } else {
      newSelected.delete(filename)
    }
    setSelectedFiles(newSelected)
  }

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
    return <div className="document-list-loading">載入中...</div>
  }

  if (error) {
    return <div className="document-list-error">{error}</div>
  }

  return (
    <div className="document-list-container">
      <div className="document-list-header">
        <h2>文件管理</h2>
        <div className="stats-summary">
          <span className="stat-item">總計: {stats.indexed + stats.modified + stats.new + stats.deleted || 0}</span>
          <span className="stat-item indexed">已索引: {stats.indexed || 0}</span>
          <span className="stat-item modified">已修改: {stats.modified || 0}</span>
          <span className="stat-item new">新文件: {stats.new || 0}</span>
          <span className="stat-item deleted">已刪除: {stats.deleted || 0}</span>
        </div>
      </div>

      <div className="document-list-controls">
        <div className="filter-controls">
          <label>篩選狀態：</label>
          <select 
            value={statusFilter || ''} 
            onChange={(e) => setStatusFilter(e.target.value || null)}
          >
            <option value="">全部</option>
            <option value="indexed">已索引</option>
            <option value="modified">已修改</option>
            <option value="new">新文件</option>
            <option value="deleted">已刪除</option>
          </select>
        </div>

        <div className="action-controls">
          <button 
            onClick={handleSync} 
            disabled={syncing}
            className="btn-sync"
            title="重新掃描文件目錄並更新狀態"
          >
            {syncing ? '同步中...' : '🔄 重新整理'}
          </button>
          <button 
            onClick={handleReindex} 
            disabled={reindexing || selectedFiles.size === 0}
            className="btn-reindex"
          >
            {reindexing ? '索引中...' : `重新索引 (${selectedFiles.size})`}
          </button>
          {stats.deleted > 0 && (
            <button 
              onClick={handleCleanup} 
              disabled={loading}
              className="btn-cleanup"
              title="清理已刪除文件的索引和資料庫記錄"
            >
              🗑️ 清理已被移除的文件 ({stats.deleted})
            </button>
          )}
        </div>
      </div>

      <table className="documents-table">
        <thead>
          <tr>
            <th>
              <input 
                type="checkbox" 
                checked={selectedFiles.size === documents.length && documents.length > 0}
                onChange={(e) => handleSelectAll(e.target.checked)}
              />
            </th>
            <th>文件名稱</th>
            <th>狀態</th>
            <th>索引時間</th>
            <th>更新時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {documents.length === 0 ? (
            <tr>
              <td colSpan="6" className="no-documents">
                {loading ? '載入中...' : '沒有文件記錄。請點擊「同步文件」按鈕來掃描 documents 目錄。'}
              </td>
            </tr>
          ) : (
            documents.map((doc) => (
              <tr key={doc.id} className={selectedFiles.has(doc.filename) ? 'selected' : ''}>
                <td>
                  <input 
                    type="checkbox"
                    checked={selectedFiles.has(doc.filename)}
                    onChange={(e) => handleSelectFile(doc.filename, e.target.checked)}
                  />
                </td>
                <td className="filename">{doc.filename}</td>
                <td>{getStatusBadge(doc.status)}</td>
                <td className="date">{formatDate(doc.indexed_at)}</td>
                <td className="date">{formatDate(doc.updated_at)}</td>
                <td>
                  <button 
                    className="btn-view"
                    onClick={() => onSelectDocument(doc.filename)}
                  >
                    檢視
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export default DocumentList
