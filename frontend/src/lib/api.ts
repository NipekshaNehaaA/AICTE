/**
 * Core API Client & Robustness Helper (TASK 0a)
 * - Resolves API_BASE from NEXT_PUBLIC_API_URL (default: http://127.0.0.1:8000)
 * - Always attaches active JWT Bearer token
 * - Handles 401 Unauthorized by clearing session and notifying app with clear user-facing message
 * - Returns typed ApiError with status, detail and statusText
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  statusText: string;
  data: any;

  constructor(status: number, statusText: string, data?: any, message?: string) {
    const detail = data?.detail || data?.message || message || `Request failed with status ${status} (${statusText})`;
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

export type LogoutHandler = (message: string) => void;
let globalLogoutHandler: LogoutHandler | null = null;

export function registerLogoutHandler(handler: LogoutHandler) {
  globalLogoutHandler = handler;
}

export function unregisterLogoutHandler() {
  globalLogoutHandler = null;
}

export type WorkspaceType = 'live' | 'sandbox';

export function getActiveWorkspace(): WorkspaceType {
  if (typeof window !== 'undefined') {
    const ws = localStorage.getItem('aicte_workspace');
    if (ws === 'live' || ws === 'sandbox') return ws;
  }
  return 'sandbox';
}

export function setActiveWorkspace(ws: WorkspaceType) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('aicte_workspace', ws);
    window.dispatchEvent(new CustomEvent('aicte:workspace_changed', { detail: { workspace: ws } }));
  }
}

export function getAuthTokenForWorkspace(ws: WorkspaceType = getActiveWorkspace()): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(`aicte_auth_token_${ws}`) || localStorage.getItem('aicte_auth_token');
}

export interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean;
}

export async function apiFetch<T = any>(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const { skipAuth = false, headers = {}, ...rest } = options;

  // Build target URL: if relative path, prepend API_BASE
  const url = endpoint.startsWith('http://') || endpoint.startsWith('https://')
    ? endpoint
    : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  // Prepare headers
  const reqHeaders = new Headers(headers);

  // Set active workspace header if not explicitly provided
  const activeWs = getActiveWorkspace();
  if (!reqHeaders.has('X-Workspace')) {
    reqHeaders.set('X-Workspace', activeWs);
  }

  // Attach token if available and not skipped
  if (!skipAuth && !reqHeaders.has('Authorization')) {
    const token = getAuthTokenForWorkspace(activeWs);
    if (token) {
      reqHeaders.set('Authorization', `Bearer ${token}`);
    }
  }

  // Ensure Content-Type for JSON body if not FormData
  if (rest.body && !(rest.body instanceof FormData) && !reqHeaders.has('Content-Type')) {
    reqHeaders.set('Content-Type', 'application/json');
  }

  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      headers: reqHeaders,
    });
  } catch (netErr: any) {
    throw new ApiError(
      0,
      'NetworkError',
      null,
      `Unable to connect to AICTE backend service at ${API_BASE}. Please verify server is running.`
    );
  }

  // Handle 401 Unauthorized
  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('aicte_auth_token');
      window.dispatchEvent(
        new CustomEvent('aicte:unauthorized', {
          detail: { message: 'Session expired or unauthorized. Please log in again.' },
        })
      );
    }
    if (globalLogoutHandler) {
      globalLogoutHandler('Session expired or unauthorized (HTTP 401). Please log in again.');
    }
    const errData = await res.json().catch(() => null);
    throw new ApiError(res.status, res.statusText, errData, 'Session expired or unauthorized. Please log in again.');
  }

  // Parse response
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await res.json().catch(() => null) : await res.text().catch(() => null);

  if (!res.ok) {
    throw new ApiError(res.status, res.statusText, data);
  }

  return data as T;
}

export async function apiFetchResponse(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<Response> {
  const { skipAuth = false, headers = {}, ...rest } = options;
  const url = endpoint.startsWith('http://') || endpoint.startsWith('https://')
    ? endpoint
    : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const reqHeaders = new Headers(headers);
  const activeWs = getActiveWorkspace();
  if (!reqHeaders.has('X-Workspace')) {
    reqHeaders.set('X-Workspace', activeWs);
  }
  if (!skipAuth && !reqHeaders.has('Authorization')) {
    const token = getAuthTokenForWorkspace(activeWs);
    if (token) reqHeaders.set('Authorization', `Bearer ${token}`);
  }

  let res: Response;
  try {
    res = await fetch(url, { ...rest, headers: reqHeaders });
  } catch (netErr: any) {
    throw new ApiError(
      0,
      'NetworkError',
      null,
      `Unable to connect to AICTE backend service at ${API_BASE}. Please verify server is running.`
    );
  }

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('aicte_auth_token');
      window.dispatchEvent(
        new CustomEvent('aicte:unauthorized', {
          detail: { message: 'Session expired or unauthorized. Please log in again.' },
        })
      );
    }
    if (globalLogoutHandler) {
      globalLogoutHandler('Session expired or unauthorized (HTTP 401). Please log in again.');
    }
    const errData = await res.json().catch(() => null);
    throw new ApiError(res.status, res.statusText, errData, 'Session expired or unauthorized. Please log in again.');
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    throw new ApiError(res.status, res.statusText, errData);
  }

  return res;
}
