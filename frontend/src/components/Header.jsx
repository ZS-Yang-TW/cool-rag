import './Header.css';
import { uiConfig } from '../config/ui.config';

function Header({ currentView, onViewChange }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="header-title">
            <span className="logo-icon">📚</span>
            {uiConfig.headerTitle}
          </h1>
          <p className="header-subtitle">
            {uiConfig.headerSubtitle}
          </p>
        </div>
        <nav className="header-nav">
          <button
            className={`nav-button ${currentView === 'chat' ? 'active' : ''}`}
            onClick={() => onViewChange('chat')}
          >
            💬 對話
          </button>
          <button
            className={`nav-button ${currentView === 'documents' ? 'active' : ''}`}
            onClick={() => onViewChange('documents')}
          >
            📄 文件管理
          </button>
        </nav>
      </div>
    </header>
  );
}

export default Header;
