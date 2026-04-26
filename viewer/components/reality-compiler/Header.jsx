import { Cpu } from "lucide-react";

export default function Header() {
  return (
    <header className="rc-header">
      <div className="rc-header-left">
        <div className="rc-logo">
          <Cpu size={20} strokeWidth={1.5} />
          <span className="rc-logo-text">Reality Compiler</span>
        </div>
        <span className="rc-tagline">idea → prototype → manufacturing</span>
      </div>
      <div className="rc-header-right">
        <span className="rc-header-badge">v0.1</span>
      </div>
    </header>
  );
}
