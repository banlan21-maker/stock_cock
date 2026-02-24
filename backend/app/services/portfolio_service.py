"""포트폴리오 보유 종목 CRUD + 현재가 조회 서비스."""

import asyncio
import logging
from datetime import date

from app.utils.supabase_client import get_supabase, reset_supabase
from app.services import stock_service

logger = logging.getLogger(__name__)


def _read_with_retry(fn):
    """읽기 전용 Supabase 쿼리를 실행하고, 연결 오류 시 클라이언트를 재생성해 1회 재시도한다."""
    try:
        return fn()
    except OSError as e:
        logger.warning("Supabase 연결 오류, 재시도: %s", e)
        reset_supabase()
        return fn()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_user_holdings(user_id: str) -> list[dict]:
    """Supabase에서 사용자의 보유 종목 목록을 조회한다."""
    def _do():
        r = (
            get_supabase()
            .table("portfolio_holdings")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        return r.data or []
    return _read_with_retry(_do)


def add_holding(user_id: str, data: dict) -> dict:
    """보유 종목을 추가한다."""
    supabase = get_supabase()
    row = {
        "user_id": user_id,
        "stock_code": data["stock_code"],
        "stock_name": data["stock_name"],
        "quantity": float(data["quantity"]),
        "avg_price": float(data["avg_price"]),
    }
    if data.get("bought_at"):
        row["bought_at"] = str(data["bought_at"])

    r = supabase.table("portfolio_holdings").insert(row).execute()
    return r.data[0] if r.data else {}


def update_holding(holding_id: str, user_id: str, data: dict) -> dict:
    """보유 종목을 수정한다 (user_id 소유 확인 포함)."""
    supabase = get_supabase()
    update_data = {}
    if "quantity" in data:
        update_data["quantity"] = float(data["quantity"])
    if "avg_price" in data:
        update_data["avg_price"] = float(data["avg_price"])
    if "bought_at" in data:
        update_data["bought_at"] = str(data["bought_at"]) if data["bought_at"] else None

    r = (
        supabase.table("portfolio_holdings")
        .update(update_data)
        .eq("id", holding_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not r.data:
        return {}
    return r.data[0]


def delete_holding(holding_id: str, user_id: str) -> bool:
    """보유 종목을 삭제한다. 성공 여부를 반환."""
    supabase = get_supabase()
    r = (
        supabase.table("portfolio_holdings")
        .delete()
        .eq("id", holding_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(r.data)


# ── 현재가 + 수익률 계산 ───────────────────────────────────────────────────────

def _calculate_profit(avg_price: float, current_price: float | None, quantity: float) -> dict:
    """수익률·손익·평가금액 계산."""
    invest = avg_price * quantity
    if current_price is None:
        return {
            "profit_loss": None,
            "profit_rate": None,
            "eval_amount": None,
        }
    eval_amount = current_price * quantity
    profit_loss = eval_amount - invest
    profit_rate = (profit_loss / invest * 100) if invest else 0
    return {
        "profit_loss": round(profit_loss),
        "profit_rate": round(profit_rate, 2),
        "eval_amount": round(eval_amount),
    }


async def get_holdings_with_price(user_id: str) -> dict:
    """보유 종목 + 현재가 병렬 조회 + 수익률 계산."""
    holdings = await asyncio.to_thread(get_user_holdings, user_id)
    if not holdings:
        return {
            "holdings": [],
            "summary": {
                "total_invest": 0,
                "total_eval": 0,
                "total_profit_loss": 0,
                "total_profit_rate": 0,
            },
        }

    # 현재가 병렬 조회
    async def fetch_price(code: str) -> float | None:
        try:
            result = await asyncio.to_thread(stock_service.get_stock_price, code)
            return result["current_price"] if result else None
        except Exception:
            return None

    prices = await asyncio.gather(*[fetch_price(h["stock_code"]) for h in holdings])

    enriched = []
    total_invest = 0.0
    total_eval = 0.0

    for holding, current_price in zip(holdings, prices):
        avg_price = float(holding["avg_price"])
        quantity = float(holding["quantity"])
        invest = avg_price * quantity
        profit_data = _calculate_profit(avg_price, current_price, quantity)

        total_invest += invest
        if profit_data["eval_amount"] is not None:
            total_eval += profit_data["eval_amount"]

        enriched.append({
            "id": holding["id"],
            "stock_code": holding["stock_code"],
            "stock_name": holding["stock_name"],
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": current_price,
            "bought_at": holding.get("bought_at"),
            **profit_data,
        })

    total_profit_loss = total_eval - total_invest
    total_profit_rate = (total_profit_loss / total_invest * 100) if total_invest else 0

    return {
        "holdings": enriched,
        "summary": {
            "total_invest": round(total_invest),
            "total_eval": round(total_eval),
            "total_profit_loss": round(total_profit_loss),
            "total_profit_rate": round(total_profit_rate, 2),
        },
    }
