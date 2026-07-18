import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class TradeRecord:
    id: int
    ticker: str
    entry_price: float
    take_profit: float
    stop_loss: float
    comment: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "active"
    result: Optional[str] = None
    close_reason: Optional[str] = None
    pnl_usdt: Optional[float] = None
    close_note: Optional[str] = None
    exit_price: Optional[float] = None


class TradeJournal:
    def __init__(self, storage_path: str = "data/journal.json"):
        self.storage_path = storage_path
        self._records: List[TradeRecord] = []
        self._next_id = 1
        self._load()

    def create_record(self, ticker: str, entry_price: float, take_profit: float, stop_loss: float, comment: str) -> TradeRecord:
        record = TradeRecord(
            id=self._next_id,
            ticker=ticker,
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            comment=comment,
        )
        self._records.append(record)
        self._next_id += 1
        self._save()
        return record

    def close_record(self, record_id: int, result: str, close_reason: str, pnl_usdt: float, close_note: str, exit_price: float) -> TradeRecord:
        record = self.get_record(record_id)
        if record is None:
            raise KeyError(f"Record {record_id} not found")
        record.status = "closed"
        record.result = result
        record.close_reason = close_reason
        record.pnl_usdt = pnl_usdt
        record.close_note = close_note
        record.exit_price = exit_price
        self._save()
        return record

    def get_record(self, record_id: int) -> Optional[TradeRecord]:
        for record in self._records:
            if record.id == record_id:
                return record
        return None

    def active_records(self) -> List[TradeRecord]:
        return [record for record in self._records if record.status == "active"]

    def closed_records(self) -> List[TradeRecord]:
        return [record for record in self._records if record.status == "closed"]

    def serialize(self) -> list:
        return [
            {
                "id": record.id,
                "ticker": record.ticker,
                "entry_price": record.entry_price,
                "take_profit": record.take_profit,
                "stop_loss": record.stop_loss,
                "comment": record.comment,
                "created_at": record.created_at,
                "status": record.status,
                "result": record.result,
                "close_reason": record.close_reason,
                "pnl_usdt": record.pnl_usdt,
                "close_note": record.close_note,
                "exit_price": record.exit_price,
            }
            for record in self._records
        ]

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        with open(self.storage_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self._records = [TradeRecord(**item) for item in data]
        self._next_id = max((record.id for record in self._records), default=0) + 1

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(self.serialize(), handle, ensure_ascii=False, indent=2)
