import unittest

from app.journal import TradeJournal


class JournalTests(unittest.TestCase):
    def test_create_and_close_record(self):
        journal = TradeJournal()
        record = journal.create_record("BTCUSDT", 100.0, 110.0, 95.0, "Long bias")

        self.assertEqual(record.status, "active")

        closed = journal.close_record(record.id, "win", "take_profit", 15.0, "Reached TP", 110.0)

        self.assertEqual(closed.status, "closed")
        self.assertEqual(closed.result, "win")
        self.assertEqual(closed.close_reason, "take_profit")
        self.assertEqual(closed.pnl_usdt, 15.0)


if __name__ == "__main__":
    unittest.main()
