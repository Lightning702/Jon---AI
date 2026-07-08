const { spawn } = require("node:child_process");
const path = require("node:path");
const electron = require("electron");

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
delete env.NODE_OPTIONS;

const appDir = path.join(__dirname, "..");
const child = spawn(electron, [appDir], {
  stdio: "inherit",
  env,
  windowsHide: false,
});
child.on("close", (code) => process.exit(code == null ? 0 : code));
