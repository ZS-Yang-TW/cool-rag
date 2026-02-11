import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import './Message.css';
import SourceCard from './SourceCard';

function Message({ message, onEditAndResend }) {
  const [showSources, setShowSources] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(message.content);
  const [copied, setCopied] = useState(false);

  const handleEditClick = () => {
    setIsEditing(true);
    setEditedContent(message.content);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedContent(message.content);
  };

  const handleSaveEdit = () => {
    if (editedContent.trim() && editedContent !== message.content) {
      onEditAndResend(message.id, editedContent.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className={`message message-${message.type} ${isEditing ? 'editing' : ''}`}>
      <div className="message-content">
        {message.type === 'user' ? (
          isEditing ? (
            <div className="message-edit-container">
              <textarea
                className="message-edit-input"
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                onKeyDown={handleKeyDown}
                autoFocus
              />
              <div className="message-edit-actions">
                <button className="message-edit-cancel" onClick={handleCancelEdit}>
                  取消
                </button>
                <button className="message-edit-save" onClick={handleSaveEdit}>
                  發送
                </button>
              </div>
            </div>
          ) : (
            <p>{message.content}</p>
          )
        ) : message.type === 'assistant' ? (
          <div className="assistant-message">
            <div className="markdown-content">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  img: ({ node, ...props }) => {
                    // Convert relative image URLs to absolute backend URLs
                    const apiBaseUrl = import.meta.env.VITE_API_URL;
                    const src = props.src?.startsWith('/images/') 
                      ? `${apiBaseUrl}${props.src}`
                      : props.src;
                    
                    return (
                      <img
                        {...props}
                        src={src}
                        style={{
                          maxWidth: '100%',
                          height: 'auto',
                          borderRadius: '8px',
                          margin: '12px 0',
                          display: 'block'
                        }}
                        loading="lazy"
                      />
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {message.sources && message.sources.length > 0 && (
              <div className="sources-section">
                <button
                  className="sources-toggle"
                  onClick={() => setShowSources(!showSources)}
                >
                  <span className="sources-icon">📄</span>
                  {showSources ? '隱藏' : '顯示'}來源 ({message.sources.length})
                </button>

                {showSources && (
                  <div className="sources-list">
                    {message.sources.map((source, index) => (
                      <SourceCard key={index} source={source} index={index + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="error-content">{message.content}</p>
        )}
      </div>

      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString('zh-TW', {
          hour: '2-digit',
          minute: '2-digit'
        })}
      </div>

      {message.type === 'user' && !isEditing && (
        <div className="message-actions">
          <button className="message-action-button" onClick={handleCopy} title="複製">
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M3 11V3C3 2.44772 3.44772 2 4 2H10" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
            )}
          </button>
          <button className="message-action-button" onClick={handleEditClick} title="編輯並重新提問">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M11.5 2.5L13.5 4.5L5.5 12.5H3.5V10.5L11.5 2.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10 4L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      )}

      {message.type === 'assistant' && (
        <div className="message-actions">
          <button className="message-action-button" onClick={handleCopy} title="複製">
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M3 11V3C3 2.44772 3.44772 2 4 2H10" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default Message;
