export function passwordPolicyError(password: string): string {
  const characters = Array.from(password);
  if (password.length > 256 || characters.length < 15 || characters.length > 128 || hasUnpairedSurrogate(password) || characters.some(character => /\p{Cc}/u.test(character))) {
    return "Use 15–128 Unicode characters without control characters.";
  }
  return "";
}

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (Number.isNaN(next) || next < 0xdc00 || next > 0xdfff) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}
