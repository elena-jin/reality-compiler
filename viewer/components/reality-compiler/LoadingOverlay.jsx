export default function LoadingOverlay({ stage }) {
  return (
    <div className="rc-loading-overlay">
      <div className="rc-loading-content">
        <div className="rc-loading-spinner">
          <svg width="40" height="40" viewBox="0 0 40 40">
            <circle
              cx="20"
              cy="20"
              r="16"
              fill="none"
              stroke="rgba(99, 102, 241, 0.15)"
              strokeWidth="2.5"
            />
            <circle
              cx="20"
              cy="20"
              r="16"
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="80"
              strokeDashoffset="60"
              className="rc-loading-circle"
            />
          </svg>
        </div>
        <p className="rc-loading-stage">{stage}</p>
      </div>
    </div>
  );
}
