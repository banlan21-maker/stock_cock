import { createClient } from "@/utils/supabase/client";

const supabase = createClient();
import type { WatchlistItem } from "@/types";

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("watchlist")
    .select("id, user_id, stock_code, stock_name, added_at")
    .order("added_at", { ascending: false });
  if (error) return [];
  return (data as WatchlistItem[]) ?? [];
}

export async function addWatchlist(
  stockCode: string,
  stockName: string
): Promise<{ ok: boolean; error?: string }> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user)
    return { ok: false, error: "로그인이 필요합니다." };

  const { error } = await supabase.from("watchlist").upsert(
    { user_id: user.id, stock_code: stockCode, stock_name: stockName },
    { onConflict: "user_id,stock_code" }
  );
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function removeWatchlist(stockCode: string): Promise<{ ok: boolean; error?: string }> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: "로그인이 필요합니다." };

  const { error } = await supabase
    .from("watchlist")
    .delete()
    .eq("user_id", user.id)
    .eq("stock_code", stockCode);
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function isInWatchlist(stockCode: string): Promise<boolean> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return false;

  const { data } = await supabase
    .from("watchlist")
    .select("id")
    .eq("user_id", user.id)
    .eq("stock_code", stockCode)
    .maybeSingle();
  return !!data;
}
