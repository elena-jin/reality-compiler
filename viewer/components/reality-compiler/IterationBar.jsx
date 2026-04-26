import { useState, useCallback } from "react";
import { RefreshCw, ArrowRight } from "lucide-react";

const QUICK_COMMANDS = [
  "Make it smaller",
  "Reduce cost",
  "Simplify design",
  "Make it larger",
];

export default function IterationBar({ onIterate, loading }) {
  const [command, setCommand] = useState("");

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (!command.trim() || loading) return;
      onIterate(command.trim());
      setCommand("");
    },
    [command, loading, onIterate]
  );

  const handleQuick = useCallback(
    (cmd) => {
      if (loading) return;
      onIterate(cmd);
    },
    [loading, onIterate]
  );

  return (
    <div className="rc-iteration-bar">
      <div className="rc-iteration-label">
        <RefreshCw size={12} strokeWidth={1.5} />
        <span>Iterate</span>
      </div>
      <div className="rc-iteration-quick">
        {QUICK_COMMANDS.map((cmd) => (
          <button
            key={cmd}
            className="rc-iteration-chip"
            onClick={() => handleQuick(cmd)}
            disabled={loading}
            type="button"
          >
            {cmd}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="rc-iteration-form">
        <input
          type="text"
          className="rc-iteration-input"
          placeholder="Custom iteration command..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="rc-iteration-submit"
          disabled={!command.trim() || loading}
        >
          <ArrowRight size={14} />
        </button>
      </form>
    </div>
  );
}
