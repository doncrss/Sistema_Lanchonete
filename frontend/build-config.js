const fs = require("node:fs");
const path = require("node:path");

const apiBaseUrl = process.env.API_BASE_URL || "http://localhost:8000";

const parsedUrl = new URL(apiBaseUrl);
if (!["http:", "https:"].includes(parsedUrl.protocol)) {
  throw new Error("API_BASE_URL precisa usar HTTP ou HTTPS.");
}

fs.writeFileSync(
  path.join(__dirname, "config.js"),
  `window.LANCHOTECH_API_URL = ${JSON.stringify(apiBaseUrl.endsWith("/") ? apiBaseUrl.slice(0, -1) : apiBaseUrl)};\n`,
);
