import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Pool } from "pg";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function loadEnvFile() {
  const envPath = path.join(rootDir, ".env");
  let body = "";
  try {
    body = await fs.readFile(envPath, "utf8");
  } catch {
    return;
  }

  for (const line of body.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const index = trimmed.indexOf("=");
    const key = trimmed.slice(0, index).trim();
    const value = trimmed.slice(index + 1).trim().replace(/^['"]|['"]$/g, "");
    if (key && process.env[key] === undefined) process.env[key] = value;
  }
}

function databaseUrl() {
  const value = process.env.DATABASE_URL;
  if (!value) {
    console.error("DATABASE_URL is required.");
    process.exit(1);
  }
  return value;
}

const sqlPath = process.argv[2];
if (!sqlPath) {
  console.error("Usage: node scripts/apply-sql.mjs <file.sql>");
  process.exit(1);
}

await loadEnvFile();

const sql = await fs.readFile(path.resolve(sqlPath), "utf8");
const pool = new Pool({ connectionString: databaseUrl() });

try {
  const result = await pool.query(sql);
  console.log(JSON.stringify({ ok: true, rows: result.rows }, null, 2));
} finally {
  await pool.end();
}
