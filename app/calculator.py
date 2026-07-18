def calculate_position_size_usdt(entry_price, stop_loss_price, leverage, risk_usdt):
    """Calculate position size in USDT and required margin.

    Formula:
    - risk distance = abs(entry - stop)
    - position size = risk_usdt / risk distance * entry_price
    - margin = position_size / leverage
    """
    if entry_price <= 0 or stop_loss_price <= 0 or leverage <= 0:
        return 0.0, 0.0

    distance = abs(entry_price - stop_loss_price)
    if distance == 0:
        return 0.0, 0.0

    position_size = (risk_usdt / distance) * entry_price
    margin = position_size / leverage
    return position_size, margin
