import math
import time


class OneEuroFilter:
    def __init__(self, mincutoff=1.0, beta=0.007, dcutoff=1.0):
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def _smoothing_factor(self, dt, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def _exponential_smoothing(self, a, raw, prev):
        return a * raw + (1.0 - a) * prev

    def apply(self, x, y):
        now = time.time()
        if self.t_prev is None:
            self.t_prev = now
            self.x_prev = (x, y)
            self.dx_prev = (0.0, 0.0)
            return x, y

        dt = now - self.t_prev
        if dt <= 0:
            dt = 1e-6

        ad = self._smoothing_factor(dt, self.dcutoff)
        dx_x = (x - self.x_prev[0]) / dt
        dx_y = (y - self.x_prev[1]) / dt
        edx_x = self._exponential_smoothing(ad, dx_x, self.dx_prev[0])
        edx_y = self._exponential_smoothing(ad, dx_y, self.dx_prev[1])
        self.dx_prev = (edx_x, edx_y)

        cutoff_x = self.mincutoff + self.beta * abs(edx_x)
        cutoff_y = self.mincutoff + self.beta * abs(edx_y)
        ax = self._smoothing_factor(dt, cutoff_x)
        ay = self._smoothing_factor(dt, cutoff_y)

        sx = self._exponential_smoothing(ax, x, self.x_prev[0])
        sy = self._exponential_smoothing(ay, y, self.x_prev[1])

        self.x_prev = (sx, sy)
        self.t_prev = now
        return sx, sy

    def reset(self):
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None