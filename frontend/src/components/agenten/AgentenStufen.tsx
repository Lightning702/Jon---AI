import {motion} from "framer-motion";
import {Check} from "lucide-react";

export default function AgentenStufen({stufen, aktuell, fertig}: {stufen: {key: string; label: string}[]; aktuell: number; fertig: boolean}) {
  const anteil = stufen.length > 1 ? Math.min(1, aktuell / (stufen.length - 1)) : 1;
  return <div className="ab-stufen" style={{["--anzahl" as string]: stufen.length}}>
    <div className="ab-stufen-schiene"><motion.span className="ab-stufen-fuellung" initial={false} animate={{width: `${anteil * 100}%`}} transition={{type: "spring", stiffness: 90, damping: 20}}/></div>
    {stufen.map((stufe, i) => {
      const erledigt = i < aktuell || (fertig && i === aktuell);
      return <div key={stufe.key} className={`ab-stufe ${erledigt ? "erledigt" : ""} ${i === aktuell && !fertig ? "jetzt" : ""}`}>
        <i>{erledigt && <motion.span initial={{scale: 0}} animate={{scale: 1}} transition={{type: "spring", stiffness: 400, damping: 16}} style={{display: "grid"}}><Check/></motion.span>}</i>
        <span>{stufe.label}</span>
      </div>;
    })}
  </div>;
}
