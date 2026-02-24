def duty_rate_contribution(source: str) -> float:
    s = (source or "").lower()
    if s in {"uk tariff", "taric"}:
        return 0.25
    return 0.1

