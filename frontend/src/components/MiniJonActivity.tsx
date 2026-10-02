import {useEffect, useRef} from "react";
import "../../electron/pet3d.js";
import "./harness-workspace.css";

type Pet = {start(): void; destroy(): void; setActivity(value: string): void; setTaskState(value: string): void};

export default function MiniJonActivity({activity = "planning", status = "idle", label = "MiniJon ist bereit"}: {activity?: string; status?: string; label?: string}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pet = useRef<Pet | null>(null);
  useEffect(() => {
    const api = (window as unknown as {Jon3D?: {create(canvas: HTMLCanvasElement): Pet | null}}).Jon3D;
    if (!canvas.current || !api) return;
    try {pet.current = api.create(canvas.current); pet.current?.start();} catch {pet.current = null;}
    return () => {pet.current?.destroy(); pet.current = null;};
  }, []);
  useEffect(() => {pet.current?.setActivity(activity); pet.current?.setTaskState(status);}, [activity, status]);
  return <div className="mini-activity" role="img" aria-label={label}><canvas ref={canvas} width={220} height={190}/><span>{label}</span></div>;
}
