import {useEffect} from "react";
import HarnessPanel from "./HarnessPanel";
import "./harness-workspace.css";

export default function HarnessWorkspace({onClose, initialTask}: {onClose: () => void; initialTask?: string}) {
  useEffect(() => {
    const key = (event: KeyboardEvent) => {if (event.key === "Escape") onClose();};
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return <div className="harness-workspace" role="dialog" aria-modal="true" aria-label="Jon Harness Arbeitsbereich"><HarnessPanel standalone onClose={onClose} initialTask={initialTask}/></div>;
}
