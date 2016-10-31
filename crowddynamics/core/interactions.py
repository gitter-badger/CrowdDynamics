import numba
import numpy as np
from numba import f8

from crowddynamics.core.vector2D import dot2d
from .power_law import force_social_circular, force_social_three_circle, \
    force_social_linear_wall
from .vector2D import length, rotate270, cross2d


@numba.jit(f8[:](f8, f8[:], f8[:], f8[:], f8, f8, f8), nopython=True,
           nogil=True)
def force_contact(h, n, v, t, mu, kappa, damping):
    """Frictional contact force with damping."""
    return - h * (mu * n - kappa * dot2d(v, t) * t) + damping * dot2d(v, n) * n


@numba.jit(nopython=True, nogil=True)
def agent_agent(agent):
    # n - 1 + n - 2 + ... + 1 = n^2 / 2 in O(n^2)
    ind = agent.indices()
    for l, i in enumerate(ind[:-1]):
        for j in ind[l + 1:]:
            agent_agent_interaction(i, j, agent)


@numba.jit(nopython=True, nogil=True)
def agent_wall(agent, wall):
    ind = agent.indices()
    for i in ind:
        for w in range(wall.size):
            agent_wall_interaction(i, w, agent, wall)


@numba.jit(nopython=True, nogil=True)
def agent_agent_distance_three_circle(agent, i, j):
    """Distance between two three-circle models.

    :param agent:
    :param i:
    :param j:
    :return:
    """
    # Positions: center, left, right
    x_i = (agent.position[i], agent.position_ls[i], agent.position_rs[i])
    x_j = (agent.position[j], agent.position_ls[j], agent.position_rs[j])

    # Radii of torso and shoulders
    r_i = (agent.r_t[i], agent.r_s[i], agent.r_s[i])
    r_j = (agent.r_t[j], agent.r_s[j], agent.r_s[j])

    # Minimizing values
    positions = np.zeros(agent.shape[1]), np.zeros(agent.shape[1])  #
    radius = (0.0, 0.0)  # Radius
    relative_distance = np.nan  # Minimum relative distance distance
    normal = np.zeros(agent.shape[1])  # Unit vector of x_rel

    for xi, ri in zip(x_i, r_i):
        for xj, rj in zip(x_j, r_j):
            x = xi - xj
            d = length(x)
            r_tot = (ri + rj)
            h = d - r_tot
            if h < relative_distance or np.isnan(relative_distance):
                relative_distance = h
                radius = ri, rj
                normal = x / d
                positions = xi, xj

    r_moment_i = positions[0] + radius[0] * normal - agent.position[i]
    r_moment_j = positions[1] - radius[1] * normal - agent.position[j]

    return normal, relative_distance, r_moment_i, r_moment_j


@numba.jit(nopython=True, nogil=True)
def agent_wall_distance(agent, wall, i, w):
    """Distance between three-circle model and a line.

    :param agent:
    :param wall:
    :param i:
    :param w:
    :return:
    """
    x_i = (agent.position[i], agent.position_ls[i], agent.position_rs[i])
    r_i = (agent.r_t[i], agent.r_s[i], agent.r_s[i])

    relative_distance = np.nan
    position = np.zeros(2)
    normal = np.zeros(2)
    radius = 0.0

    for xi, ri in zip(x_i, r_i):
        d, n = wall.distance_with_normal(w, xi)
        h = d - ri
        if h < relative_distance or np.isnan(relative_distance):
            relative_distance = h
            position = xi
            radius = ri
            normal = n

    r_moment_i = position - radius * normal - agent.position[i]

    return relative_distance, normal, r_moment_i


@numba.jit(nopython=True, nogil=True)
def agent_agent_interaction(i, j, agent):
    # Function params
    x = agent.position[i] - agent.position[j]  # Relative positions
    d = length(x)  # Distance
    r_tot = agent.radius[i] + agent.radius[j]  # Total radius
    h = d - r_tot  # Relative distance

    # Agent sees the other agent
    if d <= agent.sight_soc:
        if agent.three_circle:
            # Three circle model
            # TODO: Merge functions
            n, h, r_moment_i, r_moment_j = agent_agent_distance_three_circle(agent, i, j)
            force_i, force_j = force_social_three_circle(agent, i, j)
        else:
            # Circular model
            force_i, force_j = force_social_circular(agent, i, j)
            r_moment_i, r_moment_j = np.zeros(2), np.zeros(2)
            n = x / d  # Normal vector

        # Physical contact
        if h < 0:
            t = rotate270(n)  # Tangent vector
            v = agent.velocity[i] - agent.velocity[j]  # Relative velocity
            force_c = force_contact(h, n, v, t, agent.mu, agent.kappa,
                                    agent.damping)
            force_i += force_c
            force_j -= force_c

        agent.force[i] += force_i
        agent.force[j] += force_j
        if agent.orientable:
            agent.torque[i] += cross2d(r_moment_i, force_i)
            agent.torque[j] += cross2d(r_moment_j, force_j)

    if agent.neighbor_radius > 0 and h < agent.neighbor_radius:
        if h < agent.neighbor_distances_max[i]:
            ind = np.argmax(agent.neighbor_distances[i])
            agent.neighbors[i, ind] = j
            agent.neighbor_distances[i, ind] = h
            agent.neighbor_distances_max[i] = np.max(
                agent.neighbor_distances[i])

        if h < agent.neighbor_distances_max[j]:
            ind = np.argmax(agent.neighbor_distances[j])
            agent.neighbors[j, ind] = i
            agent.neighbor_distances[j, ind] = h
            agent.neighbor_distances_max[j] = np.max(
                agent.neighbor_distances[j])


@numba.jit(nopython=True, nogil=True)
def agent_wall_interaction(i, w, agent, wall):
    # Function params
    x = agent.position[i]
    r_tot = agent.radius[i]
    d, n = wall.distance_with_normal(w, x)
    h = d - r_tot  # Relative distance

    if h <= agent.sight_wall:
        if agent.three_circle:
            h, n, r_moment_i = agent_wall_distance(agent, wall, i, w)
            r_moment_i = np.zeros(2)
            force = force_social_linear_wall(i, w, agent, wall)
        else:
            # Circular model
            r_moment_i = np.zeros(2)
            force = force_social_linear_wall(i, w, agent, wall)

        if h < 0:
            t = rotate270(n)  # Tangent
            force_c = force_contact(h, n, agent.velocity[i], t, agent.mu,
                                    agent.kappa, agent.damping)
            force += force_c

        agent.force[i] += force
        if agent.orientable:
            agent.torque[i] += cross2d(r_moment_i, force)
