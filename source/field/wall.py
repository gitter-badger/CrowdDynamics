from collections import OrderedDict

import numpy as np
from numba import jitclass, float64, int64


spec_round = OrderedDict(
    round_params=float64[:, :],
    cols=int64,
    rows=int64,
    size=int64,
    wall=float64[:, :],
)


@jitclass(spec_round)
class RoundWall(object):
    def __init__(self, round_params):
        self.round_params = round_params
        self.cols = 3
        self.rows = len(self.round_params)
        self.wall = np.zeros((self.rows, self.cols))
        self.size = self.rows
        self.construct()

    def construct(self):
        for i in range(self.size):
            self.wall[i] = self.round_params[i]

    def deconstruct(self, index):
        if index < 0 or index >= self.size:
            raise IndexError("Index out of bounds. "
                             "Index should be: 0 <= index < size.")
        w = self.wall[index]
        p, r = w[0:2], w[2]
        return p, r

    def distance(self, i, x):
        p, r = self.deconstruct(i)
        q = x - p
        d_iw = np.hypot(q[0], q[1]) - r
        return d_iw


spec_linear = OrderedDict(
    linear_params=float64[:, :, :],
    cols=int64,
    rows=int64,
    size=int64,
    wall=float64[:, :],
)


@jitclass(spec_linear)
class LinearWall(object):
    def __init__(self, linear_params):
        self.linear_params = linear_params
        self.cols = 9
        self.rows = len(self.linear_params)
        self.wall = np.zeros(shape=(self.rows, self.cols))
        self.size = self.rows
        self.construct()

    def construct(self):
        # 90 degree counterclockwise rotation
        rot90 = np.array(((0.0, -1.0), (1.0, 0.0)))
        for i in range(self.size):
            p = self.linear_params[i]
            d = p[1] - p[0]             # Vector from p_0 to p_1
            l_w = np.hypot(d[1], d[0])  # Length of the wall
            t_w = d / l_w               # Tangential unit-vector
            n_w = np.dot(rot90, t_w)    # Normal unit-vector
            w = self.wall[i]            # Set values to wall array
            w[0:2], w[2:4], w[4:6], w[6:8], w[8] = p[0], p[1], t_w, n_w, l_w

    def deconstruct(self, index):
        if index < 0 or index >= self.size:
            raise IndexError("Index out of bounds. "
                             "Index should be: 0 <= index < size.")
        w = self.wall[index]
        p_0, p_1, t_w, n_w, l_w = w[0:2], w[2:4], w[4:6], w[6:8], w[8]
        return p_0, p_1, t_w, n_w, l_w

    def distance(self, i, x):
        """
        Linear wall i's distance from Cartesian coordinate x.
        """
        p_0, p_1, t_w, n_w, l_w = self.deconstruct(i)

        q_0 = x - p_0
        q_1 = x - p_1

        l_t = - np.dot(t_w, q_1) - np.dot(t_w, q_0)

        if l_t > l_w:
            d_iw = np.hypot(q_0[0], q_0[1])
        elif l_t < -l_w:
            d_iw = np.hypot(q_1[0], q_1[1])
        else:
            l_n = np.dot(n_w, q_0)
            d_iw = np.abs(l_n)

        return d_iw

    # TODO: distance with direction