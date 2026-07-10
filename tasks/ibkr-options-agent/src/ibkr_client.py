"""IBKR market data + order helpers via ib_insync."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from ib_insync import IB, LimitOrder, Option, Stock, util

from risk import AccountSnapshot, ProposedTrade

log = logging.getLogger(__name__)


@dataclass
class Quote:
    symbol: str
    last: float | None
    bid: float | None
    ask: float | None
    close: float | None

    @property
    def mid(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.last or self.close


@dataclass
class OptionCandidate:
    symbol: str
    expiry: str
    strike: float
    right: str
    bid: float | None
    ask: float | None
    last: float | None
    con_id: int

    @property
    def mid(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.last


class IbkrClient:
    def __init__(self, host: str, port: int, client_id: int, account_id: str = "") -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account_id = account_id
        self.ib = IB()
        self._orders_today = 0
        self._orders_day = date.today()

    def connect(self) -> None:
        log.info("Connecting IBKR %s:%s clientId=%s", self.host, self.port, self.client_id)
        self.ib.connect(self.host, self.port, clientId=self.client_id, readonly=False)
        if not self.account_id:
            accounts = self.ib.managedAccounts()
            if not accounts:
                raise RuntimeError("No managed accounts from IBKR")
            self.account_id = accounts[0]
            log.info("Using account %s", self.account_id)

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    def _bump_order_count(self) -> None:
        today = date.today()
        if today != self._orders_day:
            self._orders_day = today
            self._orders_today = 0
        self._orders_today += 1

    @property
    def orders_today(self) -> int:
        if date.today() != self._orders_day:
            return 0
        return self._orders_today

    def stock_quote(self, symbol: str) -> Quote:
        contract = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        [ticker] = self.ib.reqTickers(contract)
        return Quote(
            symbol=symbol,
            last=_num(ticker.last),
            bid=_num(ticker.bid),
            ask=_num(ticker.ask),
            close=_num(ticker.close),
        )

    def snapshot_universe(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for s in symbols:
            try:
                out[s] = self.stock_quote(s)
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.warning("quote failed for %s: %s", s, exc)
        return out

    def list_option_candidates(
        self,
        underlying: str,
        *,
        right: str,
        min_dte: int,
        max_dte: int,
        strike_band_pct: float,
        limit: int = 12,
    ) -> list[OptionCandidate]:
        stock = Stock(underlying, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        chains = self.ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
        if not chains:
            return []

        # Prefer SMART / densest chain
        chain = max(chains, key=lambda c: len(c.strikes) + len(c.expirations))
        spot_q = self.stock_quote(underlying)
        spot = spot_q.mid
        if not spot:
            return []

        today = date.today()
        lo = spot * (1 - strike_band_pct / 100.0)
        hi = spot * (1 + strike_band_pct / 100.0)
        expirations = []
        for exp in sorted(chain.expirations):
            try:
                d = datetime.strptime(exp, "%Y%m%d").date()
            except ValueError:
                continue
            dte = (d - today).days
            if min_dte <= dte <= max_dte:
                expirations.append(exp)
        if not expirations:
            return []

        # Use nearest expiry for liquidity
        expiry = expirations[0]
        strikes = [s for s in chain.strikes if lo <= s <= hi]
        strikes = sorted(strikes, key=lambda s: abs(s - spot))[:limit]

        contracts = [
            Option(underlying, expiry, strike, right.upper(), "SMART")
            for strike in strikes
        ]
        qualified = self.ib.qualifyContracts(*contracts)
        tickers = self.ib.reqTickers(*qualified) if qualified else []
        out: list[OptionCandidate] = []
        for t in tickers:
            c = t.contract
            out.append(
                OptionCandidate(
                    symbol=underlying,
                    expiry=c.lastTradeDateOrContractMonth,
                    strike=float(c.strike),
                    right=c.right,
                    bid=_num(t.bid),
                    ask=_num(t.ask),
                    last=_num(t.last),
                    con_id=int(c.conId),
                )
            )
        return out

    def account_snapshot(self) -> AccountSnapshot:
        tags = self.ib.accountSummary(self.account_id)
        equity = 0.0
        for row in tags:
            if row.tag in {"NetLiquidation", "EquityWithLoanValue"} and row.currency == "USD":
                equity = float(row.value)
                break

        open_premium = 0.0
        for pos in self.ib.positions(self.account_id):
            c = pos.contract
            if c.secType != "OPT":
                continue
            # Approximate open premium exposure with abs(avgCost)*multiplier*qty/multiplier
            # ib_insync avgCost for options is typically total cost / qty including multiplier.
            open_premium += abs(float(pos.avgCost) * float(pos.position))

        return AccountSnapshot(
            equity=equity,
            open_option_premium=open_premium,
            orders_today=self.orders_today,
        )

    def positions_brief(self) -> list[dict[str, Any]]:
        rows = []
        for pos in self.ib.positions(self.account_id):
            c = pos.contract
            rows.append(
                {
                    "secType": c.secType,
                    "symbol": c.symbol,
                    "localSymbol": getattr(c, "localSymbol", ""),
                    "right": getattr(c, "right", ""),
                    "strike": getattr(c, "strike", None),
                    "expiry": getattr(c, "lastTradeDateOrContractMonth", ""),
                    "position": float(pos.position),
                    "avgCost": float(pos.avgCost),
                }
            )
        return rows

    def place_option_limit(
        self,
        trade: ProposedTrade,
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        contract = Option(
            trade.symbol,
            trade.expiry,
            trade.strike,
            trade.right.upper(),
            "SMART",
        )
        self.ib.qualifyContracts(contract)
        order = LimitOrder(trade.action.upper(), trade.quantity, trade.limit_price)
        order.tif = "DAY"
        order.account = self.account_id

        payload = {
            "action": trade.action.upper(),
            "qty": trade.quantity,
            "limit": trade.limit_price,
            "symbol": trade.symbol,
            "expiry": trade.expiry,
            "strike": trade.strike,
            "right": trade.right.upper(),
            "localSymbol": contract.localSymbol,
            "dry_run": dry_run,
        }

        if dry_run:
            log.info("DRY_RUN order: %s", payload)
            return {**payload, "status": "dry_run"}

        trade_obj = self.ib.placeOrder(contract, order)
        self._bump_order_count()
        # Give IB a moment to ack
        self.ib.sleep(1.0)
        status = trade_obj.orderStatus.status if trade_obj.orderStatus else "submitted"
        payload["status"] = status
        payload["orderId"] = trade_obj.order.orderId
        log.info("Live order submitted: %s", payload)
        return payload


def _num(v: Any) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f or f < 0:  # NaN or IB placeholder negatives
            return None
        return f
    except (TypeError, ValueError):
        return None


def next_weekday(d: date, days: int = 1) -> date:
    out = d + timedelta(days=days)
    while out.weekday() >= 5:
        out += timedelta(days=1)
    return out


# Ensure util logging is quiet by default
util.logToConsole(logging.WARNING)
