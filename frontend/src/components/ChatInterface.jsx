import { useState } from 'react';
import { chat, clearConversation } from '../apis';
import './ChatInterface.css';
import MessageInput from './MessageInput';
import MessageList from './MessageList';
import { uiConfig } from '../config/ui.config';

function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Call API
      const response = await chat(message, conversationId);

      // Add assistant message
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }

      setIsLoading(false);
    } catch (err) {
      setError(err.message);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: `錯誤: ${err.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const handleClearChat = async () => {
    if (conversationId) {
      try {
        await clearConversation(conversationId);
      } catch (err) {
        console.error('Failed to clear conversation:', err);
      }
    }

    setMessages([]);
    setConversationId(null);
    setError(null);
  };

  const handleEditAndResend = async (messageId, newContent) => {
    // Find the index of the message being edited
    const messageIndex = messages.findIndex(msg => msg.id === messageId);
    if (messageIndex === -1) return;

    // Remove all messages after (and including) this one
    const newMessages = messages.slice(0, messageIndex);
    setMessages(newMessages);

    // Clear conversation if we're editing from the start or removing everything
    if (messageIndex === 0 || newMessages.length === 0) {
      if (conversationId) {
        try {
          await clearConversation(conversationId);
        } catch (err) {
          console.error('Failed to clear conversation:', err);
        }
      }
      setConversationId(null);
    }

    // Send the edited message as a new message
    await handleSendMessage(newContent);
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>{uiConfig.welcomeTitle}</h2>
            <p>{uiConfig.welcomeDescription}</p>
            <div className="example-questions">
              <p className="example-title">{uiConfig.exampleQuestionsTitle}</p>
              <div className="example-list">
                {uiConfig.exampleQuestions.map((question, index) => (
                  <button
                    key={index}
                    className="example-button"
                    onClick={() => handleSendMessage(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.length > 0 && (
              <div className="chat-actions">
                <button className="clear-chat-button" onClick={handleClearChat}>
                  {uiConfig.clearChatButton}
                </button>
              </div>
            )}
            <MessageList
              messages={messages}
              isLoading={isLoading}
              onEditAndResend={handleEditAndResend}
            />
          </>
        )}

        <MessageInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

export default ChatInterface;
