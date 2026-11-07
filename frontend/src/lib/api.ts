/**
 * Typed client for the DIVU AI API.
 *
 * The browser only ever talks to relative `/api/*` URLs; `next.config.ts` proxies them to the
 * FastAPI backend, so no backend host is baked into the client bundle.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
export const API_V1 = `${API_BASE}/v1`;

const ACCESS_TOKEN_KEY = "divu.access_token";
const REFRESH_TOKEN_KEY = "divu.refresh_token";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string;
    timestamp?: string;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId?: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body?.error?.message ?? `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.error?.code ?? "unknown_error";
    this.details = body?.error?.details;
    this.requestId = body?.error?.request_id;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (response.status === 401 && retry && getAccessToken()) {
    // Access tokens are short-lived; try one silent refresh before giving up.
    const refreshed = await refreshSession();
    if (refreshed) {
      return request<T>(path, init, false);
    }
  }

  if (!response.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = undefined;
    }
    throw new ApiError(
      response.status,
      body ?? { error: { code: "http_error", message: response.statusText } },
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Contracts (mirrors backend/app/schemas)
// ---------------------------------------------------------------------------

export interface BrandInfo {
  name: string;
  tagline: string;
  founder_name: string;
  founder_title: string;
}

export interface SystemInfo {
  brand: BrandInfo;
  app: string;
  version: string;
  environment: string;
  phase: string;
  features: Record<string, boolean>;
  providers: string[];
  database: string;
  cache: string;
  storage: string;
  capabilities: Record<string, boolean>;
  server_time: string;
}

export interface HealthComponent {
  name: string;
  healthy: boolean;
  detail: string;
  latency_ms: number;
}

export interface ReadyResponse {
  status: string;
  version: string;
  environment: string;
  ready: boolean;
  components: HealthComponent[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  created_at: string | null;
  last_login_at: string | null;
}

export interface ScreeningResult {
  risk_score: number;
  blocked: boolean;
  categories: string[];
  matches: string[];
  source: string;
  threshold: number;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export const api = {
  systemInfo: () => request<SystemInfo>(`${API_V1}/system/info`),
  readiness: () => request<ReadyResponse>("/health/ready"),
  liveness: () => request<{ status: string; version: string; environment: string }>("/health/live"),

  register: (email: string, password: string, fullName = "") =>
    request<UserResponse>(`${API_V1}/auth/register`, {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName }),
    }),

  login: async (email: string, password: string) => {
    const tokens = await request<TokenResponse>(`${API_V1}/auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens;
  },

  logout: async () => {
    const refresh = typeof window !== "undefined" ? window.localStorage.getItem(REFRESH_TOKEN_KEY) : null;
    try {
      if (refresh) {
        await request<{ message: string }>(`${API_V1}/auth/logout`, {
          method: "POST",
          body: JSON.stringify({ refresh_token: refresh }),
        });
      }
    } finally {
      clearTokens();
    }
  },

  me: () => request<UserResponse>(`${API_V1}/auth/me`),

  screen: (text: string, source = "user") =>
    request<ScreeningResult>(`${API_V1}/security/screen`, {
      method: "POST",
      body: JSON.stringify({ text, source }),
    }),

  audit: (params: { action?: string; outcome?: string; page_size?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.action) search.set("action", params.action);
    if (params.outcome) search.set("outcome", params.outcome);
    search.set("page_size", String(params.page_size ?? 10));
    return request<Page<Record<string, unknown>>>(`${API_V1}/audit?${search.toString()}`);
  },
};

export async function refreshSession(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const refresh = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refresh) return false;
  try {
    const response = await fetch(`${API_V1}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) {
      clearTokens();
      return false;
    }
    const tokens = (await response.json()) as TokenResponse;
    setTokens(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}
