module.exports = [
"[project]/lib/api.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "fetchDashboard",
    ()=>fetchDashboard,
    "fetchKeywordFeed",
    ()=>fetchKeywordFeed,
    "fetchNewsList",
    ()=>fetchNewsList,
    "fetchNewsSummary",
    ()=>fetchNewsSummary,
    "fetchPolicyAnalysis",
    ()=>fetchPolicyAnalysis,
    "fetchPolicyList",
    ()=>fetchPolicyList,
    "fetchStockAnalysis",
    ()=>fetchStockAnalysis,
    "fetchStockChart",
    ()=>fetchStockChart,
    "fetchStockPrice",
    ()=>fetchStockPrice,
    "fetchThemeTrend",
    ()=>fetchThemeTrend,
    "searchStocks",
    ()=>searchStocks
]);
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 20_000;
const API_TIMEOUT_LONG_MS = 60_000; // AI 분석 등 오래 걸리는 요청용
async function fetchApi(path, timeoutMs = API_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(()=>controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            cache: "no-store",
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
            const body = await res.json().catch(()=>({}));
            const message = body?.error?.message ?? body?.detail ?? `API Error: ${res.status}`;
            const err = new Error(message);
            err.code = body?.error?.code;
            throw err;
        }
        return res.json();
    } catch (e) {
        clearTimeout(timeoutId);
        if (e instanceof Error) {
            if (e.name === "AbortError") {
                throw new Error("요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.");
            }
            if (e.message?.includes("Failed to fetch") || e.cause?.code === "ECONNREFUSED") {
                throw new Error("서버에 연결할 수 없습니다. 백엔드를 먼저 실행해 주세요(예: 포트 8000).");
            }
            throw e;
        }
        throw new Error("네트워크 오류가 발생했습니다.");
    }
}
function fetchNewsList(category = "all", page = 1, limit = 10, keywords) {
    const params = new URLSearchParams({
        category,
        page: String(page),
        limit: String(limit)
    });
    if (keywords?.trim()) params.set("keywords", keywords.trim());
    return fetchApi(`/api/news?${params}`, 30_000);
}
function fetchNewsSummary(newsId) {
    return fetchApi(`/api/news/summary?id=${encodeURIComponent(newsId)}`, API_TIMEOUT_LONG_MS);
}
function fetchPolicyList(page = 1, limit = 10, keywords) {
    const params = new URLSearchParams({
        page: String(page),
        limit: String(limit)
    });
    if (keywords?.trim()) params.set("keywords", keywords.trim());
    return fetchApi(`/api/policy?${params}`);
}
function fetchPolicyAnalysis(policyId) {
    return fetchApi(`/api/policy/${policyId}/analysis`);
}
function searchStocks(query) {
    return fetchApi(`/api/stock/search?q=${encodeURIComponent(query)}`);
}
function fetchStockPrice(code) {
    return fetchApi(`/api/stock/${code}/price`);
}
function fetchStockChart(code, period = "3m", interval = "daily") {
    return fetchApi(`/api/stock/${code}/chart?period=${period}&interval=${interval}`);
}
function fetchStockAnalysis(code) {
    return fetchApi(`/api/stock/${code}/analysis`, API_TIMEOUT_LONG_MS);
}
function fetchDashboard() {
    return fetchApi(`/api/dashboard`, 30_000);
}
function fetchThemeTrend(sort = "change_rate", period = "daily") {
    return fetchApi(`/api/dashboard/theme-trend?sort=${sort}&period=${period}`, 60_000);
}
function fetchKeywordFeed(keywords) {
    return fetchApi(`/api/dashboard/keyword-feed?keywords=${encodeURIComponent(keywords)}`, 30_000);
}
}),
"[project]/lib/interestKeywords.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "INTEREST_KEYWORDS",
    ()=>INTEREST_KEYWORDS,
    "MAX_SELECTION",
    ()=>MAX_SELECTION,
    "clearInterestKeywords",
    ()=>clearInterestKeywords,
    "getInterestKeywords",
    ()=>getInterestKeywords,
    "getInterestKeywordsQuery",
    ()=>getInterestKeywordsQuery,
    "hasCompletedOnboarding",
    ()=>hasCompletedOnboarding,
    "setInterestKeywords",
    ()=>setInterestKeywords,
    "setOnboardingCompleted",
    ()=>setOnboardingCompleted,
    "setOnboardingNotCompleted",
    ()=>setOnboardingNotCompleted
]);
/** 관심 키워드: 로그인 전에는 localStorage, 로그인 후에는 사용자 설정 사용 예정 */ const STORAGE_KEY = "stockcock_interest_keywords";
const ONBOARDING_KEY = "stockcock_onboarding_done";
const INTEREST_KEYWORDS = [
    {
        id: "ai",
        label: "AI"
    },
    {
        id: "robot",
        label: "로봇"
    },
    {
        id: "quantum",
        label: "양자컴퓨터"
    },
    {
        id: "superconductor",
        label: "초전도체"
    },
    {
        id: "bio",
        label: "바이오"
    },
    {
        id: "space",
        label: "우주관련"
    },
    {
        id: "smr",
        label: "SMR (소형 모듈 원자로)"
    },
    {
        id: "power_infra",
        label: "전력 인프라 (변압기, 구리)"
    },
    {
        id: "k_defense",
        label: "K-방산 (방위산업)"
    },
    {
        id: "battery_recycle",
        label: "폐배터리 및 자원 재활용"
    },
    {
        id: "silver_tech",
        label: "실버 테크 (안티에이징/디지털 헬스케어)"
    }
];
const MAX_SELECTION = 2;
function getInterestKeywords() {
    if ("TURBOPACK compile-time truthy", 1) return [];
    //TURBOPACK unreachable
    ;
}
function setInterestKeywords(ids) {
    if ("TURBOPACK compile-time truthy", 1) return;
    //TURBOPACK unreachable
    ;
    const trimmed = undefined;
}
function hasCompletedOnboarding() {
    if ("TURBOPACK compile-time truthy", 1) return false;
    //TURBOPACK unreachable
    ;
}
function setOnboardingCompleted() {
    if ("TURBOPACK compile-time truthy", 1) return;
    //TURBOPACK unreachable
    ;
}
function setOnboardingNotCompleted() {
    if ("TURBOPACK compile-time truthy", 1) return;
    //TURBOPACK unreachable
    ;
}
function clearInterestKeywords() {
    if ("TURBOPACK compile-time truthy", 1) return;
    //TURBOPACK unreachable
    ;
}
function getInterestKeywordsQuery() {
    return getInterestKeywords().join(",");
}
;
}),
"[project]/components/ui/LoadingSpinner.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>LoadingSpinner
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
;
function LoadingSpinner({ text = "로딩 중..." }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex flex-col items-center justify-center py-12 gap-3",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "w-8 h-8 border-3 border-white/20 border-t-skyblue rounded-full animate-spin"
            }, void 0, false, {
                fileName: "[project]/components/ui/LoadingSpinner.tsx",
                lineNumber: 4,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "text-sm text-gray-400",
                children: text
            }, void 0, false, {
                fileName: "[project]/components/ui/LoadingSpinner.tsx",
                lineNumber: 5,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui/LoadingSpinner.tsx",
        lineNumber: 3,
        columnNumber: 5
    }, this);
}
}),
"[project]/components/ui/ErrorMessage.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>ErrorMessage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
"use client";
;
function ErrorMessage({ message, onRetry }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "text-red-300 text-sm mb-2",
                children: message
            }, void 0, false, {
                fileName: "[project]/components/ui/ErrorMessage.tsx",
                lineNumber: 12,
                columnNumber: 7
            }, this),
            onRetry && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                onClick: onRetry,
                className: "text-xs text-skyblue hover:text-blue-400 underline",
                children: "다시 시도"
            }, void 0, false, {
                fileName: "[project]/components/ui/ErrorMessage.tsx",
                lineNumber: 14,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui/ErrorMessage.tsx",
        lineNumber: 11,
        columnNumber: 5
    }, this);
}
}),
"[project]/lib/sanitizeTitle.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/** 뉴스 제목 정제: HTML 엔티티 디코딩, 불필요한 [태그] 제거 (프론트 방어) */ __turbopack_context__.s([
    "sanitizeNewsTitle",
    ()=>sanitizeNewsTitle
]);
function sanitizeNewsTitle(raw) {
    if (!raw || typeof raw !== "string") return "";
    let s = raw.trim();
    s = s.replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#39;/g, "'");
    s = s.replace(/^[\s\u3000]*\[[^\]]*\]\s*/, "");
    s = s.replace(/\s+/g, " ");
    return s.trim();
}
}),
"[project]/components/news/NewsCard.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>NewsCard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$sanitizeTitle$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/sanitizeTitle.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
const categoryStyles = {
    global: "bg-blue-500/20 text-blue-300",
    domestic: "bg-green-500/20 text-green-300",
    policy: "bg-purple-500/20 text-purple-300"
};
function NewsCard({ news }) {
    const style = categoryStyles[news.category] ?? "bg-gray-500/20 text-gray-300";
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
        href: `/issues/${encodeURIComponent(news.id)}`,
        className: "block bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex items-start justify-between gap-3",
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: `inline-block text-[10px] font-bold uppercase px-2 py-0.5 rounded-full mb-2 ${style}`,
                        children: news.category
                    }, void 0, false, {
                        fileName: "[project]/components/news/NewsCard.tsx",
                        lineNumber: 27,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "font-medium text-lg",
                        children: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$sanitizeTitle$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["sanitizeNewsTitle"])(news.title)
                    }, void 0, false, {
                        fileName: "[project]/components/news/NewsCard.tsx",
                        lineNumber: 32,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "text-xs text-gray-400 mt-2",
                        children: [
                            news.source,
                            " · ",
                            new Date(news.published_at).toLocaleDateString("ko-KR")
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/news/NewsCard.tsx",
                        lineNumber: 33,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/news/NewsCard.tsx",
                lineNumber: 26,
                columnNumber: 9
            }, this)
        }, void 0, false, {
            fileName: "[project]/components/news/NewsCard.tsx",
            lineNumber: 25,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/components/news/NewsCard.tsx",
        lineNumber: 21,
        columnNumber: 5
    }, this);
}
}),
"[project]/app/(app)/issues/page.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>IssuesPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$interestKeywords$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/interestKeywords.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$LoadingSpinner$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui/LoadingSpinner.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$ErrorMessage$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui/ErrorMessage.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$news$2f$NewsCard$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/news/NewsCard.tsx [app-ssr] (ecmascript)");
"use client";
;
;
;
;
;
;
;
const categories = [
    {
        value: "all",
        label: "전체"
    },
    {
        value: "global",
        label: "글로벌"
    },
    {
        value: "domestic",
        label: "국내"
    }
];
function IssuesPage() {
    const [category, setCategory] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("all");
    const [data, setData] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(true);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
    const load = ()=>{
        setLoading(true);
        setError("");
        const keywords = (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$interestKeywords$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getInterestKeywordsQuery"])();
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["fetchNewsList"])(category, 1, 10, keywords || undefined).then(setData).catch((e)=>setError(e.message)).finally(()=>setLoading(false));
    };
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        load();
    }, [
        category
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "space-y-6",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                className: "text-2xl font-bold",
                children: "국내외 이슈"
            }, void 0, false, {
                fileName: "[project]/app/(app)/issues/page.tsx",
                lineNumber: 37,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex gap-2",
                children: categories.map((c)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        onClick: ()=>setCategory(c.value),
                        className: `px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${category === c.value ? "bg-skyblue text-white" : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10"}`,
                        children: c.label
                    }, c.value, false, {
                        fileName: "[project]/app/(app)/issues/page.tsx",
                        lineNumber: 42,
                        columnNumber: 11
                    }, this))
            }, void 0, false, {
                fileName: "[project]/app/(app)/issues/page.tsx",
                lineNumber: 40,
                columnNumber: 7
            }, this),
            loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$LoadingSpinner$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {}, void 0, false, {
                fileName: "[project]/app/(app)/issues/page.tsx",
                lineNumber: 56,
                columnNumber: 19
            }, this),
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$ErrorMessage$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                message: error,
                onRetry: load
            }, void 0, false, {
                fileName: "[project]/app/(app)/issues/page.tsx",
                lineNumber: 57,
                columnNumber: 17
            }, this),
            data && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "space-y-3",
                children: data.items.map((n)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$news$2f$NewsCard$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                        news: n
                    }, n.id, false, {
                        fileName: "[project]/app/(app)/issues/page.tsx",
                        lineNumber: 62,
                        columnNumber: 13
                    }, this))
            }, void 0, false, {
                fileName: "[project]/app/(app)/issues/page.tsx",
                lineNumber: 60,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/app/(app)/issues/page.tsx",
        lineNumber: 36,
        columnNumber: 5
    }, this);
}
}),
];

//# sourceMappingURL=_554add9e._.js.map