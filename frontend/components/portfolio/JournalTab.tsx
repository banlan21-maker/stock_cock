"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Plus, Search, BookOpen, ChevronLeft, ChevronRight, X, Loader2, Sparkles } from "lucide-react";
import {
  fetchJournalEntries,
  createJournalEntry,
  updateJournalEntry,
  deleteJournalEntry,
  requestJournalAiFeedback,
} from "@/lib/portfolio";
import { searchStocks } from "@/lib/api";
import { useAd } from "@/context/AdProvider";
import type { JournalEntry, JournalCreateRequest, StockSearchResult } from "@/types";

// ── 저널 모달 ────────────────────────────────────────────────────────────────

interface JournalModalProps {
  initial: JournalEntry | null;
  onClose: () => void;
  onSubmit: (data: JournalCreateRequest) => Promise<void>;
  saving: boolean;
}

function JournalModal({ initial, onClose, onSubmit, saving }: JournalModalProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState<JournalCreateRequest>({
    stock_name: initial?.stock_name ?? "",
    stock_code: initial?.stock_code ?? "",
    action: initial?.action ?? "buy",
    trade_date: initial?.trade_date ?? today,
    price: initial?.price ?? 0,
    quantity: initial?.quantity ?? 0,
    memo: initial?.memo ?? "",
  });

  // 종목 검색 자동완성
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleNameChange(value: string) {
    setForm((prev) => ({ ...prev, stock_name: value, stock_code: "" }));

    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    if (value.trim().length < 1) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    searchDebounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const data = await searchStocks(value.trim());
        setSearchResults(data.results.slice(0, 8));
        setShowDropdown(data.results.length > 0);
      } catch {
        setSearchResults([]);
        setShowDropdown(false);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }

  function handleSelectStock(stock: StockSearchResult) {
    setForm((prev) => ({ ...prev, stock_name: stock.name, stock_code: stock.code }));
    setShowDropdown(false);
    setSearchResults([]);
  }

  function handleChange(field: keyof JournalCreateRequest, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: JournalCreateRequest = {
      ...form,
      stock_code: form.stock_code || undefined,
      memo: form.memo || undefined,
    };
    await onSubmit(payload);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="bg-[#1a1f2e] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="font-semibold text-lg">
            {initial ? "일지 수정" : "거래 기록 추가"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* 매수/매도 토글 */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => handleChange("action", "buy")}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${form.action === "buy"
                  ? "bg-red-500/30 text-red-300 border border-red-500/50"
                  : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10"
                }`}
            >
              매수
            </button>
            <button
              type="button"
              onClick={() => handleChange("action", "sell")}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${form.action === "sell"
                  ? "bg-blue-500/30 text-blue-300 border border-blue-500/50"
                  : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10"
                }`}
            >
              매도
            </button>
          </div>

          {/* 종목명 + 검색 자동완성 */}
          <div className="relative" ref={dropdownRef}>
            <label className="block text-xs text-gray-400 mb-1">종목명 *</label>
            <div className="relative">
              <input
                required
                type="text"
                value={form.stock_name}
                onChange={(e) => handleNameChange(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
                placeholder="종목명 검색 (예: 삼성전자)"
                autoComplete="off"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 pr-8 text-sm focus:outline-none focus:border-skyblue/50 placeholder-gray-600"
              />
              {searchLoading && (
                <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
              )}
            </div>

            {/* 검색 드롭다운 */}
            {showDropdown && searchResults.length > 0 && (
              <div className="absolute z-50 left-0 right-0 top-full mt-1 bg-[#1a1f2e] border border-white/20 rounded-xl shadow-2xl overflow-hidden max-h-56 overflow-y-auto">
                {searchResults.map((stock) => (
                  <button
                    key={stock.code}
                    type="button"
                    onMouseDown={(e) => { e.preventDefault(); handleSelectStock(stock); }}
                    className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/10 transition-colors text-left"
                  >
                    <span className="text-sm font-medium">{stock.name}</span>
                    <span className="text-xs text-gray-400 ml-2 shrink-0">{stock.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 종목코드 (검색 시 자동입력) */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              종목코드
              {form.stock_code && <span className="ml-1 text-green-400">✓ 자동입력됨</span>}
            </label>
            <input
              type="text"
              value={form.stock_code ?? ""}
              onChange={(e) => handleChange("stock_code", e.target.value)}
              placeholder="종목명 검색 시 자동 입력 (예: 005930)"
              maxLength={6}
              className={`w-full bg-white/5 border rounded-lg px-3 py-2 text-sm focus:outline-none placeholder-gray-600 ${
                form.stock_code ? "border-green-500/30 focus:border-green-500/50" : "border-white/10 focus:border-skyblue/50"
              }`}
            />
          </div>

          {/* 날짜 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">거래일 *</label>
            <input
              required
              type="date"
              value={form.trade_date}
              onChange={(e) => handleChange("trade_date", e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-skyblue/50"
            />
          </div>

          {/* 가격 / 수량 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">가격 (원) *</label>
              <input
                required
                type="number"
                min={1}
                value={form.price || ""}
                onChange={(e) => handleChange("price", Number(e.target.value))}
                placeholder="0"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-skyblue/50 placeholder-gray-600"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">수량 (주) *</label>
              <input
                required
                type="number"
                min={0.01}
                step="any"
                value={form.quantity || ""}
                onChange={(e) => handleChange("quantity", Number(e.target.value))}
                placeholder="0"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-skyblue/50 placeholder-gray-600"
              />
            </div>
          </div>

          {/* 총금액 미리보기 */}
          {form.price > 0 && form.quantity > 0 && (
            <p className="text-xs text-gray-400 text-right">
              총금액: <span className="text-white font-medium">{(form.price * form.quantity).toLocaleString()}원</span>
            </p>
          )}

          {/* 메모 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">메모 (선택)</label>
            <textarea
              rows={2}
              value={form.memo ?? ""}
              onChange={(e) => handleChange("memo", e.target.value)}
              placeholder="매매 이유, 느낀 점 등..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-skyblue/50 placeholder-gray-600 resize-none"
            />
          </div>

          {/* 버튼 */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm hover:bg-white/10 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-2.5 bg-skyblue text-black font-semibold rounded-lg text-sm hover:bg-skyblue/90 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  저장 중...
                </>
              ) : (
                "저장"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── 저널 카드 ────────────────────────────────────────────────────────────────

interface JournalCardProps {
  entry: JournalEntry;
  onEdit: () => void;
  onDelete: () => void;
  onAiFeedback: (entryId: string) => Promise<void>;
  aiFeedbackLoading: boolean;
}

function JournalCard({ entry, onEdit, onDelete, onAiFeedback, aiFeedbackLoading }: JournalCardProps) {
  const isBuy = entry.action === "buy";
  const dateStr = entry.trade_date.slice(0, 10);

  return (
    <div className={`bg-white/5 border rounded-xl p-4 space-y-2 ${isBuy ? "border-red-500/20" : "border-blue-500/20"}`}>
      {/* 상단: 종목 정보 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className={`shrink-0 text-[11px] px-2 py-0.5 rounded-full font-bold ${isBuy
              ? "bg-red-500/20 text-red-400 border border-red-500/30"
              : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
            }`}>
            {isBuy ? "매수" : "매도"}
          </span>
          <span className="font-medium truncate">{entry.stock_name}</span>
          {entry.stock_code && (
            <span className="text-xs text-gray-500">({entry.stock_code})</span>
          )}
        </div>
        {/* 수정/삭제 버튼 */}
        <div className="flex gap-1.5 shrink-0">
          <button
            onClick={onEdit}
            className="text-xs text-gray-400 hover:text-skyblue transition-colors px-2 py-0.5 rounded border border-white/10 hover:border-skyblue/30"
          >
            수정
          </button>
          <button
            onClick={onDelete}
            className="text-xs text-gray-400 hover:text-red-400 transition-colors px-2 py-0.5 rounded border border-white/10 hover:border-red-400/30"
          >
            삭제
          </button>
        </div>
      </div>

      {/* 거래 정보 */}
      <p className="text-sm text-gray-300">
        {dateStr} &nbsp;·&nbsp;
        <span className="font-medium">{entry.price.toLocaleString()}원</span>
        <span className="text-gray-500"> × {entry.quantity}주</span>
        <span className="text-gray-400"> = {(entry.price * entry.quantity).toLocaleString()}원</span>
      </p>

      {/* 메모 */}
      {entry.memo && (
        <p className="text-sm text-gray-400 italic">"{entry.memo}"</p>
      )}

      {/* AI 피드백 */}
      {entry.ai_feedback ? (
        <div className={`rounded-lg p-3 text-sm ${isBuy
            ? "bg-red-400/10 border border-red-400/20 text-red-200"
            : "bg-blue-400/10 border border-blue-400/20 text-blue-200"
          }`}>
          <span className="text-gray-400 text-xs mr-1.5">💬 꼰대:</span>
          {entry.ai_feedback}
        </div>
      ) : (
        <button
          onClick={() => onAiFeedback(entry.id)}
          disabled={aiFeedbackLoading}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-skyblue border border-white/10 hover:border-skyblue/30 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {aiFeedbackLoading ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Sparkles className="w-3 h-3" />
          )}
          AI 한마디
        </button>
      )}
    </div>
  );
}

// ── 메인 탭 ──────────────────────────────────────────────────────────────────

export default function JournalTab() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState<JournalEntry | null>(null);
  const [saving, setSaving] = useState(false);
  const [aiFeedbackLoadingId, setAiFeedbackLoadingId] = useState<string | null>(null);
  const { requestInterstitial } = useAd();

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const PAGE_SIZE = 5;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // 검색어 debounce (300ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJournalEntries(page, debouncedQuery);
      setEntries(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, [page, debouncedQuery]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(data: JournalCreateRequest) {
    setSaving(true);
    try {
      let result;
      if (editTarget) {
        result = await updateJournalEntry(editTarget.id, data);
      } else {
        result = await createJournalEntry(data);
      }
      if (!result.ok) throw new Error(result.error);

      setShowModal(false);
      setEditTarget(null);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  }

  async function handleAiFeedback(entryId: string) {
    setAiFeedbackLoadingId(entryId);
    requestInterstitial(async () => {
      const result = await requestJournalAiFeedback(entryId);
      if (result.ok && result.data) {
        setEntries((prev) =>
          prev.map((e) => (e.id === entryId ? result.data! : e))
        );
      } else {
        alert(result.error || "AI 피드백 생성에 실패했습니다.");
      }
      setAiFeedbackLoadingId(null);
    });
  }

  async function handleDelete(entry: JournalEntry) {
    if (!confirm(`${entry.stock_name} 거래 기록을 삭제할까요?`)) return;
    const result = await deleteJournalEntry(entry.id);
    if (!result.ok) {
      alert(result.error || "삭제 실패");
      return;
    }
    // 마지막 페이지의 마지막 항목 삭제 시 이전 페이지로
    if (entries.length === 1 && page > 1) setPage((p) => p - 1);
    else await load();
  }

  return (
    <div className="space-y-4">
      {/* 상단: 검색 + 추가 버튼 */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="일지 검색..."
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-skyblue/50 placeholder-gray-600"
          />
        </div>
        <button
          onClick={() => { setEditTarget(null); setShowModal(true); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-skyblue text-black font-semibold rounded-lg text-sm hover:bg-skyblue/90 transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          기록 추가
        </button>
      </div>

      {/* 에러 */}
      {error && (
        <div className="bg-red-400/10 border border-red-400/20 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* 목록 */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400 gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">불러오는 중...</span>
        </div>
      ) : entries.length === 0 ? (
        <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-gray-400">
          <BookOpen className="w-8 h-8 mx-auto mb-3 opacity-30" />
          {debouncedQuery ? (
            <p className="text-lg">검색 결과가 없어요.</p>
          ) : (
            <>
              <p className="text-lg mb-2">투자일지가 없어요.</p>
              <p className="text-sm mb-6">거래 기록을 추가하면 꼰대 AI가 피드백을 남겨드려요.</p>
              <button
                onClick={() => { setEditTarget(null); setShowModal(true); }}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-skyblue text-black font-semibold rounded-lg text-sm"
              >
                <Plus className="w-4 h-4" />
                첫 기록 추가하기
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <JournalCard
              key={entry.id}
              entry={entry}
              onEdit={() => { setEditTarget(entry); setShowModal(true); }}
              onDelete={() => handleDelete(entry)}
              onAiFeedback={handleAiFeedback}
              aiFeedbackLoading={aiFeedbackLoadingId === entry.id}
            />
          ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`w-8 h-8 rounded-lg text-sm transition-colors ${p === page
                  ? "bg-white/20 text-white font-semibold"
                  : "text-gray-400 hover:text-white hover:bg-white/10"
                }`}
            >
              {p}
            </button>
          ))}

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 모달 */}
      {showModal && (
        <JournalModal
          initial={editTarget}
          onClose={() => { setShowModal(false); setEditTarget(null); }}
          onSubmit={handleSubmit}
          saving={saving}
        />
      )}
    </div>
  );
}
