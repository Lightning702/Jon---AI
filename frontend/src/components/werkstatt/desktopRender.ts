import { ansichtSeiteUrl, dateiAnsicht, dateiAnsichtStand } from "../../lib/api";
import type { RenderQuelle } from "../../lib/werkstatt";

export const desktopRender: RenderQuelle = {
  starten: async (pfad) => (await dateiAnsicht(pfad)).render,
  stand: async (pfad) => (await dateiAnsichtStand(pfad)).render,
  seite: (pfad, nr, version) => ansichtSeiteUrl(pfad, nr, version),
};
