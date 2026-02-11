import { useState } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import DocumentList from './components/DocumentList'
import DocumentViewer from './components/DocumentViewer'
import Header from './components/Header'

function App() {
  const [currentView, setCurrentView] = useState('chat') // 'chat' or 'documents'
  const [selectedDocument, setSelectedDocument] = useState(null)

  const handleViewChange = (view) => {
    setCurrentView(view)
    setSelectedDocument(null)
  }

  const handleSelectDocument = (filename) => {
    setSelectedDocument(filename)
  }

  const handleCloseViewer = () => {
    setSelectedDocument(null)
  }

  return (
    <div className="App">
      <Header currentView={currentView} onViewChange={handleViewChange} />
      {currentView === 'chat' ? (
        <ChatInterface />
      ) : (
        <DocumentList onSelectDocument={handleSelectDocument} />
      )}
      {selectedDocument && (
        <DocumentViewer 
          filename={selectedDocument} 
          onClose={handleCloseViewer}
        />
      )}
    </div>
  )
}

export default App
