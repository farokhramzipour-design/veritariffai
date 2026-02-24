from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext


getcontext().prec = 28


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def quantize(self, exp: str = "0.01") -> "Money":
        q = Decimal(exp)
        return Money(self.amount.quantize(q, rounding=ROUND_HALF_UP), self.currency)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, scalar: Decimal) -> "Money":
        return Money(self.amount * scalar, self.currency)
