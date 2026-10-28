import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import { buildApiEnvironment, parseApiEnvironment } from "./dev-api-env.mjs";

// Keep credentials in the API process only. Vite must not receive this file.
let localEnvironment = {};
try {
  localEnvironment = parseApiEnvironment(await readFile(new URL("../../.env", import.meta.url), "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
// Root .env contributes only Accounts settings; process variables retain precedence.
const apiEnvironment = buildApiEnvironment(localEnvironment, process.env);

const projectPath = fileURLToPath(new URL("../../GrumPlates/GrumPlates.csproj", import.meta.url));
const apiOrigin = new URL(apiEnvironment.REACT_API_ORIGIN ?? "https://localhost:7186").origin;
const child = spawn(
  "dotnet",
  [
    "run",
    "--project",
    projectPath,
    "--no-launch-profile",
    "-p:FrontendProfile=React",
    "--",
    "--urls",
    apiOrigin,
  ],
  {
    env: {
      ...apiEnvironment,
      ASPNETCORE_ENVIRONMENT: apiEnvironment.ASPNETCORE_ENVIRONMENT ?? "Development",
      Database__RunMigrationsAtStartup: apiEnvironment.Database__RunMigrationsAtStartup ?? "true",
    },
    stdio: "inherit",
    windowsHide: true,
  },
);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}

child.once("error", (error) => {
  console.error(`Could not start dotnet: ${error.message}`);
  process.exitCode = 1;
});
child.once("exit", (code, signal) => {
  process.exitCode = code ?? (signal === "SIGINT" ? 130 : 1);
});
