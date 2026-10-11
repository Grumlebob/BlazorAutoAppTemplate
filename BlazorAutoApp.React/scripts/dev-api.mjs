import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectPath = fileURLToPath(new URL("../../BlazorAutoApp/BlazorAutoApp.csproj", import.meta.url));
const apiOrigin = new URL(process.env.REACT_API_ORIGIN ?? "https://localhost:7186").origin;
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
      ...process.env,
      ASPNETCORE_ENVIRONMENT: process.env.ASPNETCORE_ENVIRONMENT ?? "Development",
      Database__RunMigrationsAtStartup: process.env.Database__RunMigrationsAtStartup ?? "true",
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
