(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/lib/api.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "fetchDashboard",
    ()=>fetchDashboard,
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
    "searchStocks",
    ()=>searchStocks
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
const API_BASE = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 15_000;
async function fetchApi(path) {
    const controller = new AbortController();
    const timeoutId = setTimeout(()=>controller.abort(), API_TIMEOUT_MS);
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
                throw new Error("요청 시간이 초과되었습니다(15초). 백엔드가 실행 중인지 확인하거나, 잠시 후 다시 시도해 주세요.");
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
    return fetchApi(`/api/news?${params}`);
}
function fetchNewsSummary(newsId) {
    return fetchApi(`/api/news/${newsId}/summary`);
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
    return fetchApi(`/api/stock/${code}/analysis`);
}
function fetchDashboard(keywords) {
    const q = keywords?.trim() ? `?keywords=${encodeURIComponent(keywords.trim())}` : "";
    return fetchApi(`/api/dashboard${q}`);
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/interestKeywords.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
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
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];
        return parsed.filter((k)=>typeof k === "string" && INTEREST_KEYWORDS.some((kw)=>kw.id === k)).slice(0, MAX_SELECTION);
    } catch  {
        return [];
    }
}
function setInterestKeywords(ids) {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    const trimmed = ids.slice(0, MAX_SELECTION);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}
function hasCompletedOnboarding() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    try {
        return localStorage.getItem(ONBOARDING_KEY) === "1";
    } catch  {
        return false;
    }
}
function setOnboardingCompleted() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    localStorage.setItem(ONBOARDING_KEY, "1");
}
function setOnboardingNotCompleted() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    localStorage.removeItem(ONBOARDING_KEY);
}
function clearInterestKeywords() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    localStorage.removeItem(STORAGE_KEY);
}
function getInterestKeywordsQuery() {
    return getInterestKeywords().join(",");
}
;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/ui/LoadingSpinner.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>LoadingSpinner
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
;
function LoadingSpinner({ text = "로딩 중..." }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex flex-col items-center justify-center py-12 gap-3",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "w-8 h-8 border-3 border-white/20 border-t-skyblue rounded-full animate-spin"
            }, void 0, false, {
                fileName: "[project]/components/ui/LoadingSpinner.tsx",
                lineNumber: 4,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
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
_c = LoadingSpinner;
var _c;
__turbopack_context__.k.register(_c, "LoadingSpinner");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/ui/ErrorMessage.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>ErrorMessage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
"use client";
;
function ErrorMessage({ message, onRetry }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "text-red-300 text-sm mb-2",
                children: message
            }, void 0, false, {
                fileName: "[project]/components/ui/ErrorMessage.tsx",
                lineNumber: 12,
                columnNumber: 7
            }, this),
            onRetry && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
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
_c = ErrorMessage;
var _c;
__turbopack_context__.k.register(_c, "ErrorMessage");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/app/(app)/policy/page.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>PolicyPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$interestKeywords$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/interestKeywords.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$LoadingSpinner$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui/LoadingSpinner.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$ErrorMessage$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui/ErrorMessage.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Building2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/building-2.js [app-client] (ecmascript) <export default as Building2>");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
;
function PolicyPage() {
    _s();
    const [data, setData] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const load = ()=>{
        setLoading(true);
        setError("");
        const keywords = (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$interestKeywords$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getInterestKeywordsQuery"])();
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchPolicyList"])(1, 10, keywords || undefined).then(setData).catch((e)=>setError(e.message)).finally(()=>setLoading(false));
    };
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "PolicyPage.useEffect": ()=>{
            load();
        }
    }["PolicyPage.useEffect"], []);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "space-y-6",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                className: "text-2xl font-bold",
                children: "정책 분석"
            }, void 0, false, {
                fileName: "[project]/app/(app)/policy/page.tsx",
                lineNumber: 31,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "text-gray-400",
                children: "정부 정책을 AI가 분석하고 수혜주를 추천합니다."
            }, void 0, false, {
                fileName: "[project]/app/(app)/policy/page.tsx",
                lineNumber: 32,
                columnNumber: 7
            }, this),
            loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$LoadingSpinner$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {}, void 0, false, {
                fileName: "[project]/app/(app)/policy/page.tsx",
                lineNumber: 34,
                columnNumber: 19
            }, this),
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2f$ErrorMessage$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                message: error,
                onRetry: load
            }, void 0, false, {
                fileName: "[project]/app/(app)/policy/page.tsx",
                lineNumber: 35,
                columnNumber: 17
            }, this),
            data && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "space-y-3",
                children: data.items.map((p)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                        href: `/policy/${p.id}`,
                        className: "block bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex items-start gap-4",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "bg-purple-500/20 p-2 rounded-lg shrink-0",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Building2$3e$__["Building2"], {
                                        className: "w-5 h-5 text-purple-400"
                                    }, void 0, false, {
                                        fileName: "[project]/app/(app)/policy/page.tsx",
                                        lineNumber: 47,
                                        columnNumber: 19
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/app/(app)/policy/page.tsx",
                                    lineNumber: 46,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "font-medium text-lg",
                                            children: p.title
                                        }, void 0, false, {
                                            fileName: "[project]/app/(app)/policy/page.tsx",
                                            lineNumber: 50,
                                            columnNumber: 19
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "text-sm text-gray-400 mt-1",
                                            children: p.department
                                        }, void 0, false, {
                                            fileName: "[project]/app/(app)/policy/page.tsx",
                                            lineNumber: 51,
                                            columnNumber: 19
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "text-sm text-gray-300 mt-2 line-clamp-2",
                                            children: p.description
                                        }, void 0, false, {
                                            fileName: "[project]/app/(app)/policy/page.tsx",
                                            lineNumber: 52,
                                            columnNumber: 19
                                        }, this),
                                        p.effective_date && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "text-xs text-gray-500 mt-2",
                                            children: [
                                                "시행일: ",
                                                p.effective_date
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/app/(app)/policy/page.tsx",
                                            lineNumber: 54,
                                            columnNumber: 21
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/app/(app)/policy/page.tsx",
                                    lineNumber: 49,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/(app)/policy/page.tsx",
                            lineNumber: 45,
                            columnNumber: 15
                        }, this)
                    }, p.id, false, {
                        fileName: "[project]/app/(app)/policy/page.tsx",
                        lineNumber: 40,
                        columnNumber: 13
                    }, this))
            }, void 0, false, {
                fileName: "[project]/app/(app)/policy/page.tsx",
                lineNumber: 38,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/app/(app)/policy/page.tsx",
        lineNumber: 30,
        columnNumber: 5
    }, this);
}
_s(PolicyPage, "Q41jxyh8yTWlcYd1EzsDAH7xR/w=");
_c = PolicyPage;
var _c;
__turbopack_context__.k.register(_c, "PolicyPage");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/node_modules/lucide-react/dist/esm/icons/building-2.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "__iconNode",
    ()=>__iconNode,
    "default",
    ()=>Building2
]);
/**
 * @license lucide-react v0.564.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/createLucideIcon.js [app-client] (ecmascript)");
;
const __iconNode = [
    [
        "path",
        {
            d: "M10 12h4",
            key: "a56b0p"
        }
    ],
    [
        "path",
        {
            d: "M10 8h4",
            key: "1sr2af"
        }
    ],
    [
        "path",
        {
            d: "M14 21v-3a2 2 0 0 0-4 0v3",
            key: "1rgiei"
        }
    ],
    [
        "path",
        {
            d: "M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2",
            key: "secmi2"
        }
    ],
    [
        "path",
        {
            d: "M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16",
            key: "16ra0t"
        }
    ]
];
const Building2 = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"])("building-2", __iconNode);
;
 //# sourceMappingURL=building-2.js.map
}),
"[project]/node_modules/lucide-react/dist/esm/icons/building-2.js [app-client] (ecmascript) <export default as Building2>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Building2",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/building-2.js [app-client] (ecmascript)");
}),
]);

//# sourceMappingURL=_6fcb36a0._.js.map