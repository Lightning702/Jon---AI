import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  fehler: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { fehler: null };

  static getDerivedStateFromError(fehler: Error): State {
    return { fehler };
  }

  componentDidCatch(fehler: Error): void {
    try {
      window.localStorage.setItem("jon_letzter_fehler", String(fehler?.stack || fehler));
    } catch {
      return;
    }
  }

  private neuLaden = () => {
    window.location.reload();
  };

  render(): ReactNode {
    const { fehler } = this.state;
    if (!fehler) return this.props.children;
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#050506] px-5 py-10 text-white/80">
        <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <div className="text-[15px] font-medium text-amber-300">
            Jon konnte die Oberfläche nicht aufbauen
          </div>
          <p className="mt-2 text-[12.5px] leading-relaxed text-white/60">
            Ein Teil der Oberfläche hat einen Fehler gemeldet. Lade die Seite neu —
            bleibt es dabei, hilft der Fehlertext unten weiter.
          </p>
          <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-black/40 p-3 text-[11px] leading-relaxed text-white/50">
            {String(fehler?.stack || fehler?.message || fehler)}
          </pre>
          <button
            onClick={this.neuLaden}
            className="mt-4 w-full rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-[12.5px] text-amber-200 hover:bg-amber-400/20"
          >
            Seite neu laden
          </button>
        </div>
      </div>
    );
  }
}
