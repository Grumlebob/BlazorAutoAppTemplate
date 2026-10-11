import { randomBytes } from "node:crypto";
import { spawn, spawnSync } from "node:child_process";
import { rmSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const npmExecPath = process.env.npm_execpath;

if (!npmExecPath) {
  console.error("npm_execpath is missing; run this command through npm run dev.");
  process.exit(2);
}

const certificateCheck = spawnSync("dotnet", ["dev-certs", "https", "--check", "--trust"], {
  stdio: "ignore",
  windowsHide: true,
});

if (certificateCheck.error || certificateCheck.status !== 0) {
  console.error("A trusted ASP.NET Core HTTPS development certificate is required.");
  console.error("Run `dotnet dev-certs https --trust` once, then retry npm run dev.");
  process.exit(1);
}

const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "blazorautoapp-react-vite-"));
process.once("exit", () => rmSync(temporaryRoot, { recursive: true, force: true }));
const certificatePath = path.join(temporaryRoot, "localhost.pfx");
const certificatePassword = randomBytes(32).toString("base64url");

try {
  const exportResult = spawnSync(
    "dotnet",
    ["dev-certs", "https", "--export-path", certificatePath, "--password", certificatePassword],
    { stdio: "ignore", windowsHide: true },
  );

  if (exportResult.error) {
    throw exportResult.error;
  }
  if (exportResult.status !== 0) {
    throw new Error(`dotnet dev-certs exited with status ${exportResult.status ?? "unknown"}.`);
  }

  const apiOrigin = new URL(process.env.REACT_API_ORIGIN ?? "https://localhost:7186").origin;
  console.log("React dev server: https://localhost:5173");
  console.log(`API proxy:        ${apiOrigin}/api`);

  const certificateBase64 = (await readFile(certificatePath)).toString("base64");
  await rm(temporaryRoot, { recursive: true, force: true });

  const child = spawn(process.execPath, [npmExecPath, "run", "dev:vite"], {
    cwd: packageRoot,
    env: {
      ...process.env,
      NODE_USE_SYSTEM_CA: "1",
      REACT_VITE_TLS_CERTIFICATE_BASE64: certificateBase64,
      REACT_VITE_TLS_CERTIFICATE_PASSWORD: certificatePassword,
    },
    stdio: "inherit",
    windowsHide: true,
  });

  const signalHandlers = new Map();
  for (const signal of ["SIGINT", "SIGTERM"]) {
    const handler = () => child.kill(signal);
    signalHandlers.set(signal, handler);
    process.on(signal, handler);
  }

  try {
    const exitCode = await new Promise((resolve, reject) => {
      child.once("error", reject);
      child.once("exit", (code, signal) => {
        resolve(code ?? (signal === "SIGINT" ? 130 : 1));
      });
    });
    process.exitCode = exitCode;
  } finally {
    for (const [signal, handler] of signalHandlers) {
      process.off(signal, handler);
    }
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}
