def duty_rate_contribution(source: str) -> float:
    s = (source or "").lower()
    if s in {"uk tariff", "taric"}:
        return 0.25
    return 0.1


def score_hs_confidence(hs_code: str, ai_confidence: int) -> int:
    if not hs_code:
        return 0
    code = hs_code.replace(".", "").replace(" ", "")
    digits = len(code.rstrip("0"))
    if digits >= 10:
        penalty = 0
    elif digits >= 8:
        penalty = 5
    elif digits >= 6:
        penalty = 15
    else:
        penalty = 25
    v = ai_confidence - penalty
    if v < 0:
        return 0
    if v > 100:
        return 100
    return v
