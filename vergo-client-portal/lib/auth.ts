import fs from "fs";
import path from "path";
import crypto from "crypto";

export type ClientAccount = {
  clientName: string;
  slug: string;
  email: string;
  passwordHash: string;
  intakeFolderId: string;
  clientOutputFolderId?: string;
  active: boolean;
  createdAt: string;
};

const CLIENT_ACCOUNTS_PATH = path.resolve(process.cwd(), "../data/client_accounts.json");
const LEGACY_CLIENT_USERS_PATH = path.resolve(process.cwd(), "../data/client_users.json");
const ITERATIONS = 250000;
const KEYLEN = 32;
const DIGEST = "sha256";
const HASH_ALGORITHM = "pbkdf2_sha256";

async function ensureAccountsFile(): Promise<void> {
  await fs.promises.mkdir(path.dirname(CLIENT_ACCOUNTS_PATH), { recursive: true });

  if (fs.existsSync(CLIENT_ACCOUNTS_PATH)) {
    return;
  }

  if (fs.existsSync(LEGACY_CLIENT_USERS_PATH)) {
    try {
      const legacyBody = await fs.promises.readFile(LEGACY_CLIENT_USERS_PATH, "utf-8");
      const legacyUsers = JSON.parse(legacyBody) as Array<Record<string, unknown>>;
      const migrated = legacyUsers
        .map((user) => {
          const clientName = String(user["client_name"] || "").trim();
          const email = String(user["username"] || "").trim().toLowerCase();
          const slug = String(user["client_slug"] || "").trim().toLowerCase();
          const password = String(user["password"] || "").trim();
          const intakeFolderId = String(user["drive_folder_id"] || "").trim();

          if (!clientName || !email || !slug || !password || !intakeFolderId) {
            return null;
          }

          return {
            clientName,
            slug,
            email,
            passwordHash: hashPassword(password),
            intakeFolderId,
            active: true,
            createdAt: new Date().toISOString(),
          } as ClientAccount;
        })
        .filter((item): item is ClientAccount => item !== null);

      await fs.promises.writeFile(CLIENT_ACCOUNTS_PATH, JSON.stringify(migrated, null, 2), "utf-8");
      return;
    } catch {
      // If migration fails, fall back to empty file.
    }
  }

  await fs.promises.writeFile(CLIENT_ACCOUNTS_PATH, "[]", "utf-8");
}

export async function loadClientAccounts(): Promise<ClientAccount[]> {
  await ensureAccountsFile();
  try {
    const raw = await fs.promises.readFile(CLIENT_ACCOUNTS_PATH, "utf-8");
    return JSON.parse(raw) as ClientAccount[];
  } catch {
    return [];
  }
}

export async function saveClientAccounts(accounts: ClientAccount[]): Promise<void> {
  await ensureAccountsFile();
  await fs.promises.writeFile(CLIENT_ACCOUNTS_PATH, JSON.stringify(accounts, null, 2), "utf-8");
}

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const derivedKey = crypto.pbkdf2Sync(password, salt, ITERATIONS, KEYLEN, DIGEST).toString("hex");
  return `${HASH_ALGORITHM}$${ITERATIONS}$${salt}$${derivedKey}`;
}

export function verifyPassword(password: string, passwordHash: string): boolean {
  const parts = passwordHash.split("$");
  if (parts.length !== 4) {
    return false;
  }

  const [algorithm, iterationsText, salt, storedHash] = parts;
  if (algorithm !== HASH_ALGORITHM) {
    return false;
  }

  const iterations = Number(iterationsText);
  if (!Number.isInteger(iterations) || iterations <= 0) {
    return false;
  }

  const derivedKey = crypto.pbkdf2Sync(password, salt, iterations, KEYLEN, DIGEST).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(derivedKey, "hex"), Buffer.from(storedHash, "hex"));
}

export function findClientByEmail(accounts: ClientAccount[], email: string) {
  return accounts.find((item) => item.email.toLowerCase() === email.toLowerCase());
}

export function findClientBySlug(accounts: ClientAccount[], slug: string) {
  return accounts.find((item) => item.slug.toLowerCase() === slug.toLowerCase());
}
