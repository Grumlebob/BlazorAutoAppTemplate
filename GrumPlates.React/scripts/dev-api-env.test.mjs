import { describe, expect, it } from "vitest";
import { buildApiEnvironment, parseApiEnvironment } from "./dev-api-env.mjs";

describe("React API development environment", () => {
  it("loads only root Accounts settings and preserves process precedence and special characters", () => {
    const localEnvironment = parseApiEnvironment([
      "Accounts__Enabled=true",
      "Accounts__AdminSeed__Email=seed@example.test",
      String.raw`Accounts__AdminSeed__Password= spaces # $ = "quoted" `,
      "Accounts__Email__Username=mail-user",
      "Accounts__NotReviewed__Password=must-not-enter-the-api",
      "Database__Password=file-database-secret",
      "VITE_ACCOUNTS_SECRET=file-vite-secret",
    ].join("\n"));
    const processEnvironment = {
      Accounts__Enabled: "false",
      Accounts__AdminSeed__Email: "process@example.test",
      Database__Password: "process-database-secret",
    };

    const result = buildApiEnvironment(localEnvironment, processEnvironment);

    expect(result.Accounts__Enabled).toBe("false");
    expect(result.Accounts__AdminSeed__Email).toBe("process@example.test");
    expect(result.Accounts__AdminSeed__Password).toBe(' spaces # $ = "quoted" ');
    expect(result.Accounts__Email__Username).toBe("mail-user");
    expect(result.Database__Password).toBe("process-database-secret");
    expect(result.VITE_ACCOUNTS_SECRET).toBeUndefined();
  });
});
