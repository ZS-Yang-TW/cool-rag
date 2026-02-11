import { useEffect, useRef } from 'react';
import LoadingIndicator from './LoadingIndicator';
import Message from './Message';
import './MessageList.css';

function MessageList({ messages, isLoading, onEditAndResend }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="message-list">
      <div className="messages-container">
        {messages.map((message) => (
          <Message key={message.id} message={message} onEditAndResend={onEditAndResend} />
        ))}
        {isLoading && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
} export default MessageList;
