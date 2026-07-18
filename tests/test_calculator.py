import unittest

from app.calculator import calculate_position_size_usdt


class CalculatorTests(unittest.TestCase):
    def test_calculates_notional_size_from_risk_and_stop(self):
        size, margin = calculate_position_size_usdt(
            entry_price=100.0,
            stop_loss_price=95.0,
            leverage=10,
            risk_usdt=100.0,
        )

        self.assertAlmostEqual(size, 2000.0)
        self.assertAlmostEqual(margin, 200.0)

    def test_returns_zero_when_stop_equals_entry(self):
        size, margin = calculate_position_size_usdt(
            entry_price=100.0,
            stop_loss_price=100.0,
            leverage=10,
            risk_usdt=100.0,
        )

        self.assertEqual(size, 0.0)
        self.assertEqual(margin, 0.0)


if __name__ == "__main__":
    unittest.main()
