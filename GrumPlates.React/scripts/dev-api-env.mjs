const API_ENVIRONMENT_KEYS = new Set([
  "Accounts__Enabled",
  "Accounts__RegistrationEnabled",
  "Accounts__PublicOrigin",
  "Accounts__Email__Host",
  "Accounts__Email__Port",
  "Accounts__Email__Security",
  "Accounts__Email__Username",
  "Accounts__Email__Password",
  "Accounts__Email__From",
  "Accounts__AdminSeed__Enabled",
  "Accounts__AdminSeed__Email",
  "Accounts__AdminSeed__Password",
]);

export function parseApiEnvironment(contents) {
  const values = {};
  for (const line of contents.split(/\r?\n/u)) {
    const trimmed = line.trimStart();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) continue;
    const key = line.slice(0, separator).trim();
    if (API_ENVIRONMENT_KEYS.has(key)) values[key] = line.slice(separator + 1);
  }
  return values;
}

export function buildApiEnvironment(localEnvironment, processEnvironment) {
  return { ...localEnvironment, ...processEnvironment };
}
