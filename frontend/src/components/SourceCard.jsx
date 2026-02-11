import './SourceCard.css';

function SourceCard({ source, index }) {
  return (
    <div className="source-card">
      <div className="source-header">
        <span className="source-number">{index}</span>
        <div className="source-info">
          <div className="source-file">{source.file}</div>
          {source.heading && (
            <div className="source-heading">{source.heading}</div>
          )}
        </div>
        <div className="source-score">
          {(source.relevance_score * 100).toFixed(0)}%
        </div>
      </div>

      {source.content_preview && (
        <div className="source-preview">
          {source.content_preview}
        </div>
      )}
    </div>
  );
}

export default SourceCard;
