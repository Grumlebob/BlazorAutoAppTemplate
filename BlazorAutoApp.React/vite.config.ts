import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const certificateBase64 = process.env.REACT_VITE_TLS_CERTIFICATE_BASE64;

export default defineConfig({
  plugins: [tailwindcss(), reactRouter()],
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    https: certificateBase64
      ? {
          pfx: Buffer.from(certificateBase64, "base64"),
          passphrase: process.env.REACT_VITE_TLS_CERTIFICATE_PASSWORD,
        }
      : undefined,
    proxy: {
      "/api": {
        target: process.env.REACT_API_ORIGIN ?? "https://localhost:7186",
        changeOrigin: true,
        secure: true,
      },
    },
  },
});
