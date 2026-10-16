#!/usr/bin/env node
import { randomUUID } from "node:crypto";
import { open, readFile, stat } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import tls from "node:tls";

function parseArguments(args) {
  const values = new Map();
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index];
    const value = args[index + 1];
    if (!name?.startsWith("--") || !value || values.has(name)) {
      throw new Error("invalid command line");
    }
    values.set(name, value);
  }

  const required = name => {
    const value = values.get(name);
    if (!value) throw new Error(`missing ${name}`);
    return value;
  };
  const portText = values.get("--port") ?? "2525";
  const port = Number(portText);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("invalid --port");
  return {
    bind: required("--bind"),
    port,
    certificate: required("--certificate"),
    key: required("--key"),
    captureDirectory: required("--capture-directory"),
  };
}

const options = parseArguments(process.argv.slice(2));
const username = process.env.SMTP_FIXTURE_USERNAME;
const password = process.env.SMTP_FIXTURE_PASSWORD;
if (!username || !password) throw new Error("SMTP fixture credentials are required");
const captureStat = await stat(options.captureDirectory);
if (!captureStat.isDirectory()) throw new Error("SMTP capture path must be a directory");
const secureContext = tls.createSecureContext({
  cert: await readFile(options.certificate),
  key: await readFile(options.key),
  minVersion: "TLSv1.2",
});

const server = net.createServer(socket => {
  let transport = socket;
  let input = Buffer.alloc(0);
  let tlsEnabled = false;
  let authenticated = false;
  let authStep = "";
  let authUser = "";
  let dataMode = false;
  let messageLines = [];

  const reply = text => transport.write(`${text}\r\n`);
  const closeQuietly = () => {
    if (tlsEnabled) process.stdout.write("SMTP connection closed\n");
    transport.destroy();
  };

  const onLine = async line => {
    if (dataMode) {
      if (line === ".") {
        dataMode = false;
        const filename = path.join(options.captureDirectory, `${randomUUID()}.eml`);
        const message = `${messageLines.join("\r\n")}\r\n`;
        try {
          const file = await open(filename, "wx", 0o600);
          try {
            await file.writeFile(message, "ascii");
          } finally {
            await file.close();
          }
          messageLines = [];
          reply("250 2.0.0 accepted");
        } catch {
          closeQuietly();
        }
      } else {
        if (messageLines.length >= 100_000) {
          reply("552 5.3.4 message too large");
          closeQuietly();
          return;
        }
        messageLines.push(line.startsWith(".") ? line.slice(1) : line);
      }
      return;
    }

    if (authStep === "username") {
      try {
        authUser = Buffer.from(line, "base64").toString("utf8");
      } catch {
        closeQuietly();
        return;
      }
      authStep = "password";
      reply("334 UGFzc3dvcmQ6");
      return;
    }
    if (authStep === "password") {
      let receivedPassword = "";
      try {
        receivedPassword = Buffer.from(line, "base64").toString("utf8");
      } catch {
        closeQuietly();
        return;
      }
      authenticated = authUser === username && receivedPassword === password;
      authStep = "";
      authUser = "";
      receivedPassword = "";
      process.stdout.write(`AUTH LOGIN ${authenticated ? "accepted" : "rejected"}\n`);
      reply(authenticated ? "235 2.7.0 authenticated" : "535 5.7.8 authentication failed");
      return;
    }

    const [verb = "", ...argumentParts] = line.split(" ");
    const argument = argumentParts.join(" ");
    const command = verb.toUpperCase();
    if (tlsEnabled) {
      const detail = command === "AUTH" ? ` ${argument.split(/\s+/, 1)[0] ?? ""}` : "";
      process.stdout.write(`SMTP command ${command}${detail}\n`);
    }
    switch (command) {
      case "EHLO":
      case "HELO":
        reply("250-localhost");
        reply(tlsEnabled ? "250-AUTH LOGIN" : "250-STARTTLS");
        reply("250 SIZE 10485760");
        break;
      case "STARTTLS":
        if (tlsEnabled) {
          reply("503 5.5.1 TLS already active");
          break;
        }
        transport.write("220 2.0.0 begin TLS\r\n", () => {
          const clearTransport = transport;
          clearTransport.removeAllListeners("data");
          transport = new tls.TLSSocket(clearTransport, { isServer: true, secureContext });
          input = Buffer.alloc(0);
          tlsEnabled = true;
          authenticated = false;
          transport.on("data", onData);
          transport.once("secure", () => process.stdout.write("TLS established\n"));
          transport.on("end", () => process.stdout.write("TLS connection ended\n"));
          transport.on("error", error => {
            const code = typeof error.code === "string" ? error.code : error.name;
            process.stdout.write(`TLS transport error ${code}\n`);
            closeQuietly();
          });
        });
        break;
      case "AUTH":
        {
          const [mechanism = "", initialResponse] = argument.split(/\s+/, 2);
          if (tlsEnabled && mechanism.toUpperCase() === "LOGIN") {
            if (initialResponse) {
              try {
                authUser = Buffer.from(initialResponse, "base64").toString("utf8");
              } catch {
                closeQuietly();
                break;
              }
              authStep = "password";
              reply("334 UGFzc3dvcmQ6");
            } else {
              authStep = "username";
              reply("334 VXNlcm5hbWU6");
            }
          } else {
            reply("504 5.5.4 unsupported authentication mechanism");
          }
        }
        break;
      case "MAIL":
      case "RCPT":
        reply(tlsEnabled && authenticated ? "250 2.1.0 accepted" : "530 5.7.0 STARTTLS authentication required");
        break;
      case "DATA":
        if (!tlsEnabled || !authenticated) {
          reply("530 5.7.0 STARTTLS authentication required");
        } else {
          dataMode = true;
          messageLines = [];
          reply("354 end with <CRLF>.<CRLF>");
        }
        break;
      case "NOOP":
      case "RSET":
        reply("250 2.0.0 ok");
        break;
      case "QUIT":
        reply("221 2.0.0 bye");
        closeQuietly();
        break;
      default:
        reply("502 5.5.1 unsupported command");
    }
  };

  const onData = chunk => {
    if (tlsEnabled) process.stdout.write(`TLS data ${chunk.length} bytes\n`);
    input = Buffer.concat([input, chunk]);
    if (input.length > 10 * 1024 * 1024) {
      closeQuietly();
      return;
    }
    for (;;) {
      const newline = input.indexOf(0x0a);
      if (newline < 0) {
        if (input.length > 8192) closeQuietly();
        return;
      }
      let line = input.subarray(0, newline);
      input = input.subarray(newline + 1);
      if (line.length > 0 && line[line.length - 1] === 0x0d) line = line.subarray(0, -1);
      if (line.length > 8192) {
        closeQuietly();
        return;
      }
      void onLine(line.toString("ascii")).catch(closeQuietly);
    }
  };

  socket.setTimeout(20_000, closeQuietly);
  socket.on("data", onData);
  socket.on("error", closeQuietly);
  reply("220 localhost fixture ready");
});

server.on("error", () => process.exit(1));
server.listen(options.port, options.bind, () => {
  const address = server.address();
  if (!address || typeof address === "string") process.exit(1);
  process.stdout.write(`READY ${address.port}\n`);
});
