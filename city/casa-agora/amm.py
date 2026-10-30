"""Pool de producto constante estilo Uniswap v2 (x * y = k). Solo simulacion.

Modelo:
- Swap de entrada exacta. La comision f se cobra sobre el input; el input completo
  entra en la reserva, asi que k = x*y crece con cada swap.
- Liquidez con acciones LP proporcionales (la primera provision mintea sqrt(x*y)).
- Sin protocol fee, sin gas, sin liquidez concentrada, sin MEV.
"""
import math


class Pool:
    def __init__(self, fee=0.003):
        if not 0.0 <= fee < 1.0:
            raise ValueError("fee debe estar en [0, 1)")
        self.fee = float(fee)
        self.x = 0.0
        self.y = 0.0
        self.total_shares = 0.0
        self.shares = {}  # dueno -> acciones LP

    # ----- consultas -------------------------------------------------------
    def price(self):
        """Precio del activo x expresado en y (y por x)."""
        if self.x <= 0.0:
            raise ValueError("pool vacio")
        return self.y / self.x

    def k(self):
        return self.x * self.y

    def share_of(self, dueno):
        if self.total_shares <= 0.0:
            return 0.0
        return self.shares.get(dueno, 0.0) / self.total_shares

    # ----- swaps (entrada exacta) -----------------------------------------
    def quote_x_in(self, dx):
        """Cuanto y sale si entran dx de x (no ejecuta)."""
        dx_ef = dx * (1.0 - self.fee)
        return self.y * dx_ef / (self.x + dx_ef)

    def swap_x_in(self, dx):
        """Entran dx de x, salen y. Devuelve (dy_salida, comision_en_x)."""
        if dx <= 0.0:
            raise ValueError("dx debe ser > 0")
        dy = self.quote_x_in(dx)
        self.x += dx
        self.y -= dy
        return dy, dx * self.fee

    def swap_y_in(self, dy):
        """Entran dy de y, salen x. Devuelve (dx_salida, comision_en_y)."""
        if dy <= 0.0:
            raise ValueError("dy debe ser > 0")
        dy_ef = dy * (1.0 - self.fee)
        dx = self.x * dy_ef / (self.y + dy_ef)
        self.y += dy
        self.x -= dx
        return dx, dy * self.fee

    # ----- liquidez --------------------------------------------------------
    def add_liquidity(self, dueno, dx, dy):
        """Aporta (dx, dy) en proporcion al pool. Devuelve (acciones, dx_usado, dy_usado).

        Si el aporte no es proporcional, solo se usa la parte que cabe en la
        proporcion actual; lo sobrante no entra (queda en manos del aportante).
        """
        if dx <= 0.0 or dy <= 0.0:
            raise ValueError("aportes deben ser > 0")
        if self.total_shares == 0.0:
            s = math.sqrt(dx * dy)
            used_x, used_y = dx, dy
        else:
            s = min(dx * self.total_shares / self.x, dy * self.total_shares / self.y)
            used_x = s * self.x / self.total_shares
            used_y = s * self.y / self.total_shares
        self.x += used_x
        self.y += used_y
        self.total_shares += s
        self.shares[dueno] = self.shares.get(dueno, 0.0) + s
        return s, used_x, used_y

    def remove_liquidity(self, dueno, s):
        """Retira s acciones del dueno. Devuelve (dx, dy) recibidos."""
        tenia = self.shares.get(dueno, 0.0)
        if s <= 0.0 or s > tenia * (1.0 + 1e-12):
            raise ValueError("acciones insuficientes")
        s = min(s, tenia)
        dx = s * self.x / self.total_shares
        dy = s * self.y / self.total_shares
        self.x -= dx
        self.y -= dy
        self.total_shares -= s
        self.shares[dueno] = max(0.0, tenia - s)
        return dx, dy
