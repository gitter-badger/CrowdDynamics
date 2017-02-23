import numba
import numpy as np
from numba import typeof, int64


# Default values
from crowddynamics.core.vector.vector2D import unit_vector, rotate270

tau_adj = 0.5
tau_rot = 0.2
k_soc = 1.5
tau_0 = 3.0
mu = 1.2e5
kappa = 4e4
damping = 500
std_rand_force = 0.1
std_rand_torque = 0.1


# Limits
sight_soc = 3.0
sight_wall = 3.0
f_soc_ij_max = 2e3
f_soc_iw_max = 2e3


# Agent attributes
translational = [
    ('mass', np.float64),
    ('radius', np.float64),
    ('position', np.float64, 2),
    ('velocity', np.float64, 2),
    ('target_velocity', np.float64),
    ('target_direction', np.float64, 2),
    ('force', np.float64, 2),
    ('tau_adj', np.float64),
    ('k_soc', np.float64),
    ('tau_0', np.float64),
    ('mu', np.float64),
    ('kappa', np.float64),
    ('damping', np.float64),
    ('std_rand_force', np.float64),
    ('f_soc_ij_max', np.float64),
    ('f_soc_iw_max', np.float64),
    ('sight_soc', np.float64),
    ('sight_wall', np.float64),
]

rotational = [
    ('inertia_rot', np.float64),
    ('orientation', np.float64),
    ('angular_velocity', np.float64),
    ('target_orientation', np.float64),
    ('target_angular_velocity', np.float64),
    ('torque', np.float64),
    ('tau_rot', np.float64),
    ('std_rand_torque', np.float64),
]

three_circle = [
    ('r_t', np.float64),
    ('r_s', np.float64),
    ('r_ts', np.float64),
]

# Agent types
agent_type_circular = np.dtype(
    translational
)

agent_type_three_circle = np.dtype(
    translational +
    rotational +
    three_circle
)


@numba.jit((typeof(agent_type_three_circle), int64),
           nopython=True, nogil=True, cache=True)
def shoulders(agent, i):
    n = agent.orientation[i]
    t = rotate270(n)
    offset = t * agent.r_ts[i]
    position = agent.position[i]
    position_ls = position - offset
    position_rs = position + offset
    return position, position_ls, position_rs


@numba.jit((typeof(agent_type_three_circle), int64),
           nopython=True, nogil=True, cache=True)
def front(agent, i):
    return agent.position[i] * unit_vector(agent.orientation[i]) * agent.r_t[i]


@numba.jit()
def reset_motion(agent):
    agent.force[:] = 0
    agent.torque[:] = 0


class AgentFactory(object):
    def __init__(self, size, model):
        self.agents = np.zeros(size, dtype=agent_type_circular)


# Linear obstacle defined by two points
obstacle_type_linear = np.dtype([
    ('p0', np.float64, 2),
    ('p1', np.float64, 2),
])