import { useState } from "react";
import JonGeraetAssistent from "./JonGeraetAssistent";
import HandyModalLegacy from "./HandyModalLegacy";

export default function HandyModal({ onClose }: { onClose: () => void }) {
  const [legacy, setLegacy] = useState(false);
  return legacy ? <HandyModalLegacy onClose={onClose} /> : <JonGeraetAssistent onClose={onClose} onLegacy={() => setLegacy(true)} />;
}
