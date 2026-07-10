import crypto from "node:crypto";
import http from "node:http";
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
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

await loadEnvFile();

const appPort = Number(process.env.APP_PORT || process.env.PORT || 3002);

function resolveDatabaseUrl() {
  const value = process.env.DATABASE_URL || "postgres://gata_admin:change-me-admin-password@localhost:5432/gata_league";
  if (process.env.RUNNING_IN_DOCKER === "true") {
    return value;
  }

  try {
    const url = new URL(value);
    if (url.hostname === "postgres") {
      url.hostname = "localhost";
      url.port = process.env.POSTGRES_PORT || "5432";
      return url.toString();
    }
  } catch {
    return value;
  }

  return value;
}

const databaseUrl = resolveDatabaseUrl();
const sessionDays = Number(process.env.SESSION_DAYS || 30);
const databaseCheckRetries = Number(process.env.DATABASE_CHECK_RETRIES || 30);
const databaseCheckDelayMs = Number(process.env.DATABASE_CHECK_DELAY_MS || 1000);

const pool = new Pool({ connectionString: databaseUrl });
const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"],
]);

function normalizeLogin(value = "") {
  return String(value).toLowerCase().replace(/\s+/g, " ").trim();
}

function publicUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    login: row.login,
    telegram: row.telegram,
    isAdmin: row.is_admin,
    createdAt: row.created_at,
  };
}

function publicSavedTeam(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    baseTeamSlug: row.base_team_slug,
    logoData: row.logo_data,
    roster: row.roster,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function hashToken(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const derived = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt:${salt}:${derived}`;
}

function verifyPassword(password, stored = "") {
  const [method, salt, expected] = stored.split(":");
  if (method !== "scrypt" || !salt || !expected) return false;
  const actual = crypto.scryptSync(password, salt, 64);
  return crypto.timingSafeEqual(Buffer.from(expected, "hex"), actual);
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function safeDatabaseLabel(value = "") {
  try {
    const url = new URL(value);
    return `${url.hostname}:${url.port || 5432}/${url.pathname.replace(/^\//, "")}`;
  } catch {
    return "configured database";
  }
}

function startupLog(message) {
  console.log(`[startup] ${message}`);
}

async function waitForDatabase() {
  const label = safeDatabaseLabel(databaseUrl);
  startupLog(`checking PostgreSQL at ${label}`);

  for (let attempt = 1; attempt <= databaseCheckRetries; attempt += 1) {
    try {
      await pool.query("SELECT 1");
      startupLog(`PostgreSQL is up, site is connected to ${label}`);
      return;
    } catch (error) {
      const isLastAttempt = attempt === databaseCheckRetries;
      const detail = error?.code || error?.message || "connection failed";
      if (isLastAttempt) {
        startupLog(`PostgreSQL check failed after ${attempt} attempts: ${detail}`);
        throw error;
      }
      startupLog(`PostgreSQL is not ready yet (${attempt}/${databaseCheckRetries}): ${detail}`);
      await wait(databaseCheckDelayMs);
    }
  }
}

async function ensureSchema() {
  const sql = await fs.readFile(path.join(rootDir, "server", "init.sql"), "utf8");
  await pool.query(sql);
  startupLog("database schema is ready");
}

async function ensureAdmin() {
  const login = process.env.ADMIN_LOGIN || "admin";
  const password = process.env.ADMIN_PASSWORD || "change-me-site-admin-password";
  const telegram = process.env.ADMIN_TELEGRAM || "@admin";
  const loginKey = normalizeLogin(login);
  const passwordHash = hashPassword(password);

  await pool.query(
    `INSERT INTO users (login, login_key, telegram, password_hash, is_admin)
     VALUES ($1, $2, $3, $4, TRUE)
     ON CONFLICT (login_key) DO UPDATE
       SET telegram = EXCLUDED.telegram,
           password_hash = EXCLUDED.password_hash,
           is_admin = TRUE,
           updated_at = now()`,
    [login, loginKey, telegram, passwordHash],
  );
  startupLog(`admin account is ready: ${login}`);
}

function sendJson(response, status, payload) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

function bearerToken(request) {
  const header = request.headers.authorization || "";
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match?.[1] ?? "";
}

async function currentUser(request) {
  const token = bearerToken(request);
  if (!token) return null;
  const tokenHash = hashToken(token);
  const result = await pool.query(
    `SELECT users.*
     FROM sessions
     JOIN users ON users.id = sessions.user_id
     WHERE sessions.token_hash = $1 AND sessions.expires_at > now()`,
    [tokenHash],
  );
  return result.rows[0] ?? null;
}

async function createSession(userId) {
  const token = crypto.randomBytes(32).toString("base64url");
  await pool.query(
    `INSERT INTO sessions (token_hash, user_id, expires_at)
     VALUES ($1, $2, now() + ($3 || ' days')::interval)`,
    [hashToken(token), userId, String(sessionDays)],
  );
  return token;
}

async function handleApi(request, response, url) {
  try {
    if (request.method === "GET" && url.pathname === "/api/health") {
      await pool.query("SELECT 1");
      return sendJson(response, 200, { ok: true });
    }

    if (request.method === "GET" && url.pathname === "/api/auth/me") {
      const user = await currentUser(request);
      return sendJson(response, 200, { user: publicUser(user) });
    }

    if (request.method === "POST" && url.pathname === "/api/auth/register") {
      const body = await readJson(request);
      const login = String(body.login ?? "").trim();
      const password = String(body.password ?? "");
      const telegram = String(body.telegram ?? "").trim();
      const loginKey = normalizeLogin(login);

      if (login.length < 3) return sendJson(response, 400, { error: "Login must be at least 3 characters." });
      if (password.length < 4) return sendJson(response, 400, { error: "Password must be at least 4 characters." });
      if (!telegram) return sendJson(response, 400, { error: "Telegram contact is required." });

      const passwordHash = hashPassword(password);
      const result = await pool.query(
        `INSERT INTO users (login, login_key, telegram, password_hash)
         VALUES ($1, $2, $3, $4)
         RETURNING *`,
        [login, loginKey, telegram, passwordHash],
      ).catch((error) => {
        if (error.code === "23505") return null;
        throw error;
      });
      if (!result) return sendJson(response, 409, { error: "This login is already registered." });

      const token = await createSession(result.rows[0].id);
      return sendJson(response, 201, { token, user: publicUser(result.rows[0]) });
    }

    if (request.method === "POST" && url.pathname === "/api/auth/login") {
      const body = await readJson(request);
      const loginKey = normalizeLogin(body.login ?? "");
      const password = String(body.password ?? "");
      const result = await pool.query("SELECT * FROM users WHERE login_key = $1", [loginKey]);
      const user = result.rows[0];
      if (!user || !verifyPassword(password, user.password_hash)) {
        return sendJson(response, 401, { error: "Wrong login or password." });
      }
      const token = await createSession(user.id);
      return sendJson(response, 200, { token, user: publicUser(user) });
    }

    if (request.method === "POST" && url.pathname === "/api/auth/logout") {
      const token = bearerToken(request);
      if (token) {
        await pool.query("DELETE FROM sessions WHERE token_hash = $1", [hashToken(token)]);
      }
      return sendJson(response, 200, { ok: true });
    }

    if (request.method === "PATCH" && url.pathname === "/api/auth/profile") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });

      const body = await readJson(request);
      const login = String(body.login ?? user.login).trim();
      const telegram = String(body.telegram ?? user.telegram).trim();
      const password = String(body.password ?? "");
      const loginKey = normalizeLogin(login);

      if (login.length < 3) return sendJson(response, 400, { error: "Login must be at least 3 characters." });
      if (!telegram) return sendJson(response, 400, { error: "Telegram contact is required." });
      if (password && password.length < 4) return sendJson(response, 400, { error: "Password must be at least 4 characters." });

      const params = [user.id, login, loginKey, telegram];
      const passwordSql = password ? ", password_hash = $5" : "";
      if (password) params.push(hashPassword(password));
      const updated = await pool.query(
        `UPDATE users
         SET login = $2,
             login_key = $3,
             telegram = $4,
             updated_at = now()
             ${passwordSql}
         WHERE id = $1
         RETURNING *`,
        params,
      ).catch((error) => {
        if (error.code === "23505") return null;
        throw error;
      });
      if (!updated) return sendJson(response, 409, { error: "This login is already registered." });

      return sendJson(response, 200, { user: publicUser(updated.rows[0]) });
    }

    if (url.pathname === "/api/teams" && request.method === "GET") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });
      const result = await pool.query(
        `SELECT * FROM saved_teams WHERE user_id = $1 ORDER BY updated_at DESC`,
        [user.id],
      );
      return sendJson(response, 200, { teams: result.rows.map(publicSavedTeam) });
    }

    if (url.pathname === "/api/teams" && request.method === "POST") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });
      const body = await readJson(request);
      const name = String(body.name ?? "").trim();
      const baseTeamSlug = String(body.baseTeamSlug ?? "").trim();
      const logoData = body.logoData ? String(body.logoData) : null;
      const roster = body.roster ?? {};

      if (!name) return sendJson(response, 400, { error: "Team name is required." });
      if (!baseTeamSlug) return sendJson(response, 400, { error: "Base team is required." });
      if (logoData && Buffer.byteLength(logoData, "utf8") > 2_900_000) {
        return sendJson(response, 400, { error: "Logo is too large." });
      }

      const result = await pool.query(
        `INSERT INTO saved_teams (user_id, name, base_team_slug, logo_data, roster)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING *`,
        [user.id, name, baseTeamSlug, logoData, JSON.stringify(roster)],
      );
      return sendJson(response, 201, { team: publicSavedTeam(result.rows[0]) });
    }

    const teamMatch = url.pathname.match(/^\/api\/teams\/([0-9a-f-]+)$/i);
    if (teamMatch && request.method === "GET") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });
      const result = await pool.query(
        `SELECT * FROM saved_teams WHERE id = $1 AND user_id = $2`,
        [teamMatch[1], user.id],
      );
      if (!result.rows[0]) return sendJson(response, 404, { error: "Team not found." });
      return sendJson(response, 200, { team: publicSavedTeam(result.rows[0]) });
    }

    if (teamMatch && request.method === "PATCH") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });
      const body = await readJson(request);
      const name = String(body.name ?? "").trim();
      const baseTeamSlug = String(body.baseTeamSlug ?? "").trim();
      const logoData = body.logoData ? String(body.logoData) : null;
      const roster = body.roster ?? {};

      if (!name) return sendJson(response, 400, { error: "Team name is required." });
      if (!baseTeamSlug) return sendJson(response, 400, { error: "Base team is required." });
      if (logoData && Buffer.byteLength(logoData, "utf8") > 2_900_000) {
        return sendJson(response, 400, { error: "Logo is too large." });
      }

      const result = await pool.query(
        `UPDATE saved_teams
         SET name = $3,
             base_team_slug = $4,
             logo_data = $5,
             roster = $6,
             updated_at = now()
         WHERE id = $1 AND user_id = $2
         RETURNING *`,
        [teamMatch[1], user.id, name, baseTeamSlug, logoData, JSON.stringify(roster)],
      );
      if (!result.rows[0]) return sendJson(response, 404, { error: "Team not found." });
      return sendJson(response, 200, { team: publicSavedTeam(result.rows[0]) });
    }

    if (teamMatch && request.method === "DELETE") {
      const user = await currentUser(request);
      if (!user) return sendJson(response, 401, { error: "Not authorized." });
      await pool.query(`DELETE FROM saved_teams WHERE id = $1 AND user_id = $2`, [teamMatch[1], user.id]);
      return sendJson(response, 200, { ok: true });
    }

    return sendJson(response, 404, { error: "API route not found." });
  } catch (error) {
    console.error(error);
    return sendJson(response, 500, { error: "Server error." });
  }
}

function resolveStaticPath(url) {
  const cleanPath = decodeURIComponent(url.pathname);
  const target = cleanPath === "/" ? "index.html" : cleanPath.slice(1);
  const fullPath = path.resolve(rootDir, target);
  return fullPath.startsWith(rootDir) ? fullPath : null;
}

async function handleStatic(_request, response, url) {
  const fullPath = resolveStaticPath(url);
  if (!fullPath) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  try {
    const body = await fs.readFile(fullPath);
    response.writeHead(200, {
      "Content-Type": mimeTypes.get(path.extname(fullPath)) || "application/octet-stream",
    });
    response.end(body);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
  }
}

await waitForDatabase();
await ensureSchema();
await ensureAdmin();

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://localhost:${appPort}`);
  if (url.pathname.startsWith("/api/")) {
    await handleApi(request, response, url);
    return;
  }
  await handleStatic(request, response, url);
});

server.listen(appPort, () => {
  startupLog(`Gata League site and API are running at http://localhost:${appPort}`);
});
