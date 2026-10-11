import { spawnSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(packageRoot, "..");
const projectPath = path.join(repositoryRoot, "BlazorAutoApp", "BlazorAutoApp.csproj");
const expectedSchemaPath = path.join(packageRoot, "api", "openapi.json");
const expectedTypesPath = path.join(packageRoot, "app", "api", "generated", "schema.d.ts");
const mode = process.argv[2];

if (mode !== "generate" && mode !== "check") {
  console.error("Usage: node scripts/openapi-contract.mjs <generate|check>");
  process.exit(2);
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    env: {
      ...process.env,
      DOTNET_CLI_TELEMETRY_OPTOUT: "1",
      DOTNET_NOLOGO: "1",
    },
    stdio: "inherit",
    windowsHide: true,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(`${path.basename(command)} exited with status ${result.status ?? "unknown"}.`);
  }
}

function normalizeText(value) {
  return value.replaceAll("\r\n", "\n").replaceAll("\r", "\n").replace(/\n*$/, "\n");
}

function temporaryPath(root, candidate) {
  const resolvedRoot = path.resolve(root);
  const resolvedCandidate = path.resolve(candidate);
  const relative = path.relative(resolvedRoot, resolvedCandidate);

  if (relative === "" || relative.startsWith(`..${path.sep}`) || relative === ".." || path.isAbsolute(relative)) {
    throw new Error(`Temporary output escaped its owned directory: ${candidate}`);
  }

  return resolvedCandidate;
}

async function generateInto(temporaryRoot) {
  const artifactPath = temporaryPath(temporaryRoot, path.join(temporaryRoot, "artifacts"));
  const documentDirectory = temporaryPath(temporaryRoot, path.join(temporaryRoot, "documents"));
  const schemaPath = temporaryPath(temporaryRoot, path.join(temporaryRoot, "openapi.json"));
  const typesPath = temporaryPath(temporaryRoot, path.join(temporaryRoot, "schema.d.ts"));

  run("dotnet", [
    "build",
    projectPath,
    "--configuration",
    "Release",
    "--artifacts-path",
    artifactPath,
    "-p:FrontendProfile=React",
    "-p:OpenApiGenerateDocumentsOnBuild=true",
    `-p:OpenApiDocumentsDirectory=${documentDirectory}`,
  ], repositoryRoot);

  const generatedDocumentPath = path.join(documentDirectory, "BlazorAutoApp.json");
  const documentText = normalizeText(await readFile(generatedDocumentPath, "utf8"));
  const document = JSON.parse(documentText);

  if (document.openapi !== "3.1.1") {
    throw new Error(`Expected OpenAPI 3.1.1, received ${document.openapi ?? "no version"}.`);
  }
  if (Object.hasOwn(document, "servers")) {
    throw new Error("The same-origin API contract must not include server URLs.");
  }

  await writeFile(schemaPath, documentText, "utf8");

  const npmExecPath = process.env.npm_execpath;
  if (!npmExecPath) {
    throw new Error("npm_execpath is missing; run this command through the package's npm script.");
  }

  run(process.execPath, [npmExecPath, "run", "api:typegen", "--", schemaPath, "--output", typesPath], packageRoot);
  const typesText = normalizeText(await readFile(typesPath, "utf8"));

  return { documentText, typesText };
}

async function readExpected(filePath) {
  try {
    return normalizeText(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }

    throw error;
  }
}

async function writeGenerated(filePath, contents) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, contents, "utf8");
}

const tempRoot = await mkdtemp(path.join(os.tmpdir(), "blazorautoapp-openapi-"));
try {
  const trustedTempRoot = await realpath(os.tmpdir());
  const ownedTempRoot = await realpath(tempRoot);
  const relative = path.relative(trustedTempRoot, ownedTempRoot);
  if (relative === "" || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`Refusing to clean temporary output outside the system temp directory: ${ownedTempRoot}`);
  }

  const generated = await generateInto(ownedTempRoot);
  if (mode === "generate") {
    await writeGenerated(expectedSchemaPath, generated.documentText);
    await writeGenerated(expectedTypesPath, generated.typesText);
    console.log("Updated api/openapi.json and app/api/generated/schema.d.ts.");
  } else {
    const differences = [];
    if ((await readExpected(expectedSchemaPath)) !== generated.documentText) {
      differences.push("api/openapi.json");
    }
    if ((await readExpected(expectedTypesPath)) !== generated.typesText) {
      differences.push("app/api/generated/schema.d.ts");
    }

    if (differences.length > 0) {
      console.error(`OpenAPI contract drift: ${differences.join(", ")}. Run npm run api:generate and review the changes.`);
      process.exitCode = 1;
    } else {
      console.log("OpenAPI schema and TypeScript declarations are up to date.");
    }
  }
} finally {
  await rm(tempRoot, { recursive: true, force: true });
}
