import { useState, useCallback } from "react";
import { ArrowRight, Sparkles, Clock } from "lucide-react";

const EXAMPLE_PROMPTS = [
  "Robotic gripper with servo-actuated fingers",
  "Self-watering plant pot with moisture sensor",
  "Coin sorting machine for UK currency",
  "Adjustable desk lamp with USB-C power",
  "Phone stand with cable management",
  "Mini quadcopter drone frame",
];

export default function InputPanel({ onGenerate, loading, history }) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (!prompt.trim() || loading) return;
      onGenerate(prompt.trim());
    },
    [prompt, loading, onGenerate]
  );

  const handleExample = useCallback(
    (example) => {
      setPrompt(example);
    },
    []
  );

  return (
    <div className="rc-panel rc-input-panel">
      <div className="rc-panel-header">
        <Sparkles size={14} strokeWidth={1.5} />
        <span>Product Idea</span>
      </div>

      <form onSubmit={handleSubmit} className="rc-input-form">
        <textarea
          className="rc-textarea"
          placeholder="Describe your product idea..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          disabled={loading}
        />
        <button
          type="submit"
          className="rc-generate-btn"
          disabled={!prompt.trim() || loading}
        >
          {loading ? (
            <span className="rc-btn-loading">
              <span className="rc-spinner" />
              Generating...
            </span>
          ) : (
            <>
              Generate Prototype
              <ArrowRight size={14} strokeWidth={2} />
            </>
          )}
        </button>
      </form>

      <div className="rc-examples">
        <span className="rc-examples-label">Try an example</span>
        <div className="rc-examples-list">
          {EXAMPLE_PROMPTS.map((ex) => (
            <button
              key={ex}
              className="rc-example-chip"
              onClick={() => handleExample(ex)}
              disabled={loading}
              type="button"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {history.length > 1 && (
        <div className="rc-history">
          <div className="rc-history-header">
            <Clock size={12} strokeWidth={1.5} />
            <span>Session History</span>
            <span className="rc-history-count">{history.length}</span>
          </div>
          <div className="rc-history-list">
            {history.map((item, i) => (
              <div key={item.id} className="rc-history-item">
                <span className="rc-history-idx">#{i + 1}</span>
                <span className="rc-history-prompt">
                  {item.prompt.length > 40
                    ? item.prompt.slice(0, 40) + "..."
                    : item.prompt}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
