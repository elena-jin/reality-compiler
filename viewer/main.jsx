import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import RealityCompilerApp from "./components/reality-compiler/App";
import "./app/reality-compiler.css";

const ROOT_ID = "root";

function bootstrap() {
  const rootElement = document.getElementById(ROOT_ID);
  if (!rootElement) {
    throw new Error(`Missing #${ROOT_ID} mount point.`);
  }
  document.title = "Reality Compiler";
  createRoot(rootElement).render(
    <StrictMode>
      <RealityCompilerApp />
    </StrictMode>,
  );
}

bootstrap();
