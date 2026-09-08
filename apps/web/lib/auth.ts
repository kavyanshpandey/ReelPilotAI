export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("reelpilot_access_token");
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem("reelpilot_access_token", token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem("reelpilot_access_token");
  window.localStorage.removeItem("reelpilot_user");
}

export function authHeaders(json = false): HeadersInit {
  const token = getAccessToken();
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

