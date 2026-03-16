/**
 * 포트폴리오 API 클라이언트
 * - CRUD: Supabase 직접 접근 (watchlist 패턴)
 * - 현재가 포함 목록 / AI 분석: FastAPI (Bearer 토큰 인증)
 */

import { createClient } from "@/utils/supabase/client";

const supabase = createClient();
import type {
  PortfolioHolding,
  PortfolioResponse,
  PortfolioAddRequest,
  PortfolioAIAnalysis,
  PortfolioPerformanceResponse,
  JournalEntry,
  JournalListResponse,
  JournalCreateRequest,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
console.log("Portfolio API Config:", { API_BASE, NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL });

// ── 인증 헬퍼 ─────────────────────────────────────────────────────────────────

async function getAuthHeaders(): Promise<HeadersInit> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // 디버깅: 세션 및 토큰 확인
  console.log("Auth Debug:", {
    hasSession: !!session,
    hasToken: !!session?.access_token,
    user: session?.user?.email
  });

  if (!session?.access_token) {
    throw new Error("로그인이 필요합니다.");
  }
  return {
    Authorization: `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  };
}

// ── CRUD (Backend API) ───────────────────────────────────────────────────────

export async function addHolding(
  data: PortfolioAddRequest
): Promise<{ ok: boolean; error?: string; data?: PortfolioHolding }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/holdings`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }

    const result = await res.json();
    return { ok: true, data: result };
  } catch (err) {
    console.error("Add Holding Error:", err);
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function updateHolding(
  id: string,
  data: Partial<PortfolioAddRequest>
): Promise<{ ok: boolean; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/holdings/${id}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function deleteHolding(
  id: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/holdings/${id}`, {
      method: "DELETE",
      headers,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

// ── 현재가 포함 목록 (FastAPI 병렬 조회) ──────────────────────────────────────

export async function fetchPortfolioWithPrice(): Promise<PortfolioResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/portfolio/holdings`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API Error: ${res.status}`);
  }
  return res.json();
}

// ── 수익률 추이 ───────────────────────────────────────────────────────────────

export async function fetchPortfolioPerformance(days = 90): Promise<PortfolioPerformanceResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/portfolio/performance?days=${days}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API Error: ${res.status}`);
  }
  return res.json();
}

// ── 투자일지 API ──────────────────────────────────────────────────────────────

export async function fetchJournalEntries(
  page = 1,
  q = ""
): Promise<JournalListResponse> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({ page: String(page) });
  if (q) params.set("q", q);
  const res = await fetch(`${API_BASE}/api/portfolio/journal?${params}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API Error: ${res.status}`);
  }
  return res.json();
}

export async function createJournalEntry(
  data: JournalCreateRequest
): Promise<{ ok: boolean; data?: JournalEntry; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/journal`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true, data: await res.json() };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function updateJournalEntry(
  id: string,
  data: JournalCreateRequest
): Promise<{ ok: boolean; data?: JournalEntry; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/journal/${id}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true, data: await res.json() };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function deleteJournalEntry(
  id: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/journal/${id}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function requestJournalAiFeedback(
  entryId: string
): Promise<{ ok: boolean; data?: import("@/types").JournalEntry; error?: string }> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/portfolio/journal/${entryId}/ai-feedback`, {
      method: "POST",
      headers,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Error ${res.status}` };
    }
    return { ok: true, data: await res.json() };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

// ── AI 진단 ───────────────────────────────────────────────────────────────────

export async function fetchPortfolioAnalysis(): Promise<PortfolioAIAnalysis> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/portfolio/analysis`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API Error: ${res.status}`);
  }
  return res.json();
}

