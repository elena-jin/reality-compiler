import { useState, useCallback, useRef, lazy, Suspense } from "react";
import InputPanel from "./InputPanel";
import ModelViewer from "./ModelViewer";
import URDFViewer from "./URDFViewer";
import ResultsPanel from "./ResultsPanel";
import IterationBar from "./IterationBar";
import LoadingOverlay from "./LoadingOverlay";
import Header from "./Header";
import ArduinoPanel from "./ArduinoPanel";
import { Building2, Cpu, Zap } from "lucide-react";

const OfficeScene = lazy(() => import("./OfficeScene"));

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function RealityCompilerApp() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [history, setHistory] = useState([]);
  const [revealStage, setRevealStage] = useState(0);
  const [activeTab, setActiveTab] = useState("compiler");
  const [selectedPart, setSelectedPart] = useState(null);
  const abortRef = useRef(null);

  const staggerReveal = useCallback(() => {
    setRevealStage(0);
    const stages = [1, 2, 3, 4, 5, 6, 7, 8];
    stages.forEach((s, i) => {
      setTimeout(() => setRevealStage(s), 200 + i * 200);
    });
  }, []);

  const handleGenerate = useCallback(
    async (prompt) => {
      setLoading(true);
      setError(null);
      setRevealStage(0);
      setLoadingStage("Initializing agents...");
      setActiveTab("compiler");

      try {
        const stages = [
          "Analyzing product concept...",
          "Generating 3D model...",
          "Sourcing components...",
          "Assessing feasibility...",
          "Finding Shenzhen manufacturers...",
          "Compiling results...",
        ];
        let stageIdx = 0;
        const stageInterval = setInterval(() => {
          stageIdx = Math.min(stageIdx + 1, stages.length - 1);
          setLoadingStage(stages[stageIdx]);
        }, 800);

        const resp = await fetch(`${API_BASE}/api/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, session_id: sessionId }),
        });

        clearInterval(stageInterval);

        if (!resp.ok) {
          const body = await resp.text();
          throw new Error(body || `Request failed (${resp.status})`);
        }

        const data = await resp.json();
        setResult(data);
        setSessionId(data.id ? sessionId : null);
        if (!sessionId) {
          setSessionId(crypto.randomUUID());
        }
        setHistory((prev) => [...prev, data]);
        staggerReveal();
      } catch (err) {
        setError(err.message || "Something went wrong");
      } finally {
        setLoading(false);
        setLoadingStage("");
      }
    },
    [sessionId, staggerReveal]
  );

  const handleIterate = useCallback(
    async (command) => {
      if (!result || !sessionId) return;
      setLoading(true);
      setError(null);
      setLoadingStage("Iterating design...");

      try {
        const resp = await fetch(`${API_BASE}/api/iterate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            design_id: result.id,
            command,
          }),
        });

        if (!resp.ok) {
          const body = await resp.text();
          throw new Error(body || `Iteration failed (${resp.status})`);
        }

        const data = await resp.json();
        setResult(data);
        setHistory((prev) => [...prev, data]);
        staggerReveal();
      } catch (err) {
        setError(err.message || "Iteration failed");
      } finally {
        setLoading(false);
        setLoadingStage("");
      }
    },
    [result, sessionId, staggerReveal]
  );

  return (
    <div className="rc-app">
      <Header />
      <div className="rc-top-tabs">
        <button
          className={`rc-top-tab ${activeTab === "compiler" ? "rc-top-tab-active" : ""}`}
          onClick={() => setActiveTab("compiler")}
          type="button"
        >
          <Cpu size={14} />
          <span>Reality Compiler</span>
        </button>
        <button
          className={`rc-top-tab ${activeTab === "office" ? "rc-top-tab-active" : ""}`}
          onClick={() => setActiveTab("office")}
          type="button"
        >
          <Building2 size={14} />
          <span>Unicorn Mafia HQ</span>
        </button>
      </div>

      {activeTab === "compiler" ? (
        <div className="rc-main">
          <InputPanel onGenerate={handleGenerate} loading={loading} history={history} />
          <div className="rc-center">
            {result?.concept_model?.urdf_path ? (
              <URDFViewer
                urdfPath={result.concept_model.urdf_path}
                onPartSelect={setSelectedPart}
              />
            ) : (
              <ModelViewer
                model={result?.concept_model}
                loading={loading}
                onPartSelect={setSelectedPart}
              />
            )}
            {result && !loading && (
              <IterationBar onIterate={handleIterate} loading={loading} />
            )}
          </div>
          <div className="rc-right-scroll">
            <ResultsPanel
              result={result}
              loading={loading}
              revealStage={revealStage}
              error={error}
            />
            {result?.arduino && (
              <ArduinoPanel arduino={result.arduino} />
            )}
          </div>
        </div>
      ) : (
        <div className="rc-main rc-main-office">
          <Suspense
            fallback={
              <div className="rc-office-loading">
                <div className="rc-spinner" />
                <p>Loading Unicorn Mafia HQ...</p>
              </div>
            }
          >
            <OfficeScene />
          </Suspense>
        </div>
      )}
      {loading && <LoadingOverlay stage={loadingStage} />}
    </div>
  );
}
