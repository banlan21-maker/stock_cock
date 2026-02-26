const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 20_000;
const API_TIMEOUT_LONG_MS = 60_000; // AI 분석 등 오래 걸리는 요청용

async function fetchApi<T>(path: string, timeoutMs = API_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const message =
        body?.error?.message ?? body?.detail ?? `API Error: ${res.status}`;
      const err = new Error(message) as Error & { code?: string };
      err.code = body?.error?.code;
      throw err;
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof Error) {
      if (e.name === "AbortError") {
        throw new Error(
          "요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        );
      }
      if (e.message?.includes("Failed to fetch") || (e as any).cause?.code === "ECONNREFUSED") {
        throw new Error(
          "서버에 연결할 수 없습니다. 백엔드를 먼저 실행해 주세요(예: 포트 8000)."
        );
      }
      throw e;
    }
    throw new Error("네트워크 오류가 발생했습니다.");
  }
}

// News
export function fetchNewsList(
  category = "all",
  page = 1,
  limit = 10,
  keywords?: string
) {
  const params = new URLSearchParams({
    category,
    page: String(page),
    limit: String(limit),
  });
  if (keywords?.trim()) params.set("keywords", keywords.trim());
  return fetchApi<import("@/types").NewsListResponse>(`/api/news?${params}`, 30_000);
}

export function fetchNewsSummary(newsId: string) {
  return fetchApi<import("@/types").NewsArticle>(
    `/api/news/summary?id=${encodeURIComponent(newsId)}`,
    API_TIMEOUT_LONG_MS,
  );
}

// Policy
export function fetchPolicyList(page = 1, limit = 10, keywords?: string) {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (keywords?.trim()) params.set("keywords", keywords.trim());
  return fetchApi<import("@/types").PolicyListResponse>(`/api/policy?${params}`);
}

export function fetchPolicyAnalysis(policyId: string) {
  return fetchApi<import("@/types").PolicyInfo>(
    `/api/policy/${policyId}/analysis`,
    API_TIMEOUT_LONG_MS,
  );
}

// Stock
export function searchStocks(query: string) {
  return fetchApi<{ results: import("@/types").StockSearchResult[]; total: number }>(
    `/api/stock/search?q=${encodeURIComponent(query)}`
  );
}

export function fetchStockPrice(code: string) {
  return fetchApi<import("@/types").StockPrice>(
    `/api/stock/${code}/price`
  );
}

export function fetchStockChart(code: string, period = "3m", interval = "daily") {
  return fetchApi<import("@/types").ChartResponse>(
    `/api/stock/${code}/chart?period=${period}&interval=${interval}`
  );
}

export function fetchStockAnalysis(code: string) {
  return fetchApi<import("@/types").StockAnalysis>(
    `/api/stock/${code}/analysis`,
    API_TIMEOUT_LONG_MS,
  );
}

export function fetchStockCompare(codeA: string, codeB: string) {
  return fetchApi<import("@/types").StockCompareResult>(
    `/api/stock/compare?code_a=${encodeURIComponent(codeA)}&code_b=${encodeURIComponent(codeB)}`,
    API_TIMEOUT_LONG_MS,
  );
}

export type AnalysisStreamEvent =
  | { type: "status"; step: number; message: string }
  | { type: "done"; data: import("@/types").StockAnalysis }
  | { type: "error"; message: string; code?: string };

export async function* fetchStockAnalysisStream(
  code: string,
  signal?: AbortSignal,
): AsyncGenerator<AnalysisStreamEvent> {
  const res = await fetch(`${API_BASE}/api/stock/${code}/analysis/stream`, {
    cache: "no-store",
    signal,
  });

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    const message = body?.error?.message ?? body?.detail ?? `API Error: ${res.status}`;
    yield { type: "error", message };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 이벤트는 빈 줄(\n\n)로 구분
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.split("\n");
        let eventType = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7).trim();
          if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
        }
        if (!eventType || !dataStr) continue;
        try {
          const parsed = JSON.parse(dataStr);
          if (eventType === "status") {
            yield { type: "status", step: parsed.step, message: parsed.message };
          } else if (eventType === "done") {
            yield { type: "done", data: parsed as import("@/types").StockAnalysis };
          } else if (eventType === "error") {
            yield { type: "error", message: parsed.message, code: parsed.code };
          }
        } catch {
          // JSON 파싱 실패 무시
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Disclosure (DART 공시)
export function fetchTodayDisclosures(maxItems = 30) {
  return fetchApi<import("@/types").DisclosureListResponse>(
    `/api/disclosure?max_items=${maxItems}`,
    30_000,
  );
}

export function fetchDisclosureAnalysis(rcpNo: string, reportNm = "", corpName = "") {
  const params = new URLSearchParams({ report_nm: reportNm, corp_name: corpName });
  return fetchApi<import("@/types").DisclosureAnalysis>(
    `/api/disclosure/${encodeURIComponent(rcpNo)}/analysis?${params}`,
    API_TIMEOUT_LONG_MS,
  );
}

export function fetchStockDisclosures(code: string, days = 30) {
  return fetchApi<import("@/types").DisclosureListResponse>(
    `/api/stock/${code}/disclosures?days=${days}`,
  );
}

// Dashboard
export function fetchDashboard() {
  return fetchApi<import("@/types").DashboardResponse>(`/api/dashboard`, 30_000);
}

export function fetchThemeTrend(
  sort: "change_rate" | "volume" = "change_rate",
  period: "daily" | "weekly" = "daily",
) {
  return fetchApi<import("@/types").ThemeTrendResponse>(
    `/api/dashboard/theme-trend?sort=${sort}&period=${period}`,
    60_000,
  );
}

export function fetchKeywordFeed(keywords: string) {
  return fetchApi<import("@/types").KeywordFeedResponse>(
    `/api/dashboard/keyword-feed?keywords=${encodeURIComponent(keywords)}`,
    30_000,
  );
}
