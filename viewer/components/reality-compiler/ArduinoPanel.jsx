import { useState } from "react";
import { Cpu, Copy, Check, ChevronDown, ChevronRight, Zap, Cable } from "lucide-react";

export default function ArduinoPanel({ arduino }) {
  const [copied, setCopied] = useState(false);
  const [showCode, setShowCode] = useState(true);
  const [showPins, setShowPins] = useState(true);

  if (!arduino) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(arduino.code_snippet || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const wireColors = {
    red: "#ef4444",
    black: "#1a1a1e",
    orange: "#f97316",
    yellow: "#eab308",
    blue: "#3b82f6",
    green: "#22c55e",
    white: "#e2e8f0",
    purple: "#a855f7",
  };

  return (
    <div className="rc-arduino-panel">
      <div className="rc-arduino-header">
        <Cpu size={14} />
        <span>{arduino.board}</span>
        {arduino.libraries?.length > 0 && (
          <span className="rc-arduino-libs">
            {arduino.libraries.join(", ")}
          </span>
        )}
      </div>

      {/* Pin Mapping Table */}
      <button
        className="rc-arduino-section-toggle"
        onClick={() => setShowPins(!showPins)}
        type="button"
      >
        {showPins ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Cable size={12} />
        <span>Wiring Diagram ({arduino.pins?.length} connections)</span>
      </button>

      {showPins && (
        <div className="rc-arduino-pins">
          {arduino.pins?.map((pin, i) => (
            <div key={i} className="rc-arduino-pin-row">
              <span className="rc-arduino-pin-name">{pin.pin}</span>
              <span
                className="rc-arduino-wire"
                style={{
                  backgroundColor: wireColors[pin.wire_color] || "#64748b",
                }}
              />
              <span className="rc-arduino-component">{pin.component}</span>
              {pin.note && (
                <span className="rc-arduino-note">{pin.note}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Code Snippet */}
      {arduino.code_snippet && (
        <>
          <button
            className="rc-arduino-section-toggle"
            onClick={() => setShowCode(!showCode)}
            type="button"
          >
            {showCode ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <Zap size={12} />
            <span>Arduino Code</span>
            <button
              className="rc-arduino-copy"
              onClick={(e) => {
                e.stopPropagation();
                handleCopy();
              }}
              title="Copy code"
              type="button"
            >
              {copied ? <Check size={10} /> : <Copy size={10} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </button>

          {showCode && (
            <pre className="rc-arduino-code">
              <code>{arduino.code_snippet}</code>
            </pre>
          )}
        </>
      )}
    </div>
  );
}
