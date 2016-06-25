from collections import namedtuple, Iterable

import numpy as np
from scipy.stats import truncnorm as tn

from .tables.load import body_types, agent_table


class Parameters:
    """
    Generates random parameters for simulations and testing.
    """
    Lim = namedtuple('Lim', ['min', 'max'])

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = self.Lim(0.0, self.width)
        self.y = self.Lim(0.0, self.height)

    @staticmethod
    def truncnorm(loc, abs_scale, size, std=3.0):
        """Scaled symmetrical truncated normal distribution."""
        return np.array(tn.rvs(-std, std, loc=loc, scale=abs_scale / std, size=size))

    @staticmethod
    def random_unit_vector(size):
        """Random unit vector."""
        orientation = np.random.uniform(0, 2 * np.pi, size=size)
        unit_vector = np.stack((np.cos(orientation), np.sin(orientation)), axis=1)
        return unit_vector

    def random_2d_coordinates(self, size):
        """Random x and y coordinates inside dims."""
        return np.stack((np.random.uniform(*self.x, size=size),
                         np.random.uniform(*self.y, size=size)), axis=1)

    def random_position(self, position, radius, x_dims=None, y_dims=None,
                        walls=None):
        """
        Generate uniformly distributed random positions inside x_dims and y_dims
        for the agents without overlapping each others or the walls with Monte
        Carlo method.
        """
        # TODO: define area more accurately
        # TODO: check if area can be filled
        if not isinstance(walls, Iterable):
            walls = (walls,)
        walls = tuple(filter(None, walls))

        i = 0

        if x_dims is None:
            x_dims = self.x
        if y_dims is None:
            y_dims = self.y

        iterations = 0
        max_iterations = 100 * len(position)
        while i < len(position):
            if iterations >= max_iterations:
                raise Exception("Iteration limit if {} reached.".format(
                    max_iterations))
            iterations += 1

            # Random uniform position inside x and y dimensions
            pos = np.zeros(2)

            pos[0] = np.random.uniform(*x_dims)
            pos[1] = np.random.uniform(*y_dims)

            rad = radius[i]
            radii = radius[:i]

            # Test overlapping with other agents
            if i > 0:
                d = pos - position[:i]
                d = np.hypot(d[:, 0], d[:, 1]) - (rad + radii)
                cond = np.all(d > 0)
                if not cond:
                    continue

            # Test overlapping with walls
            cond = 1
            for wall in walls:
                for j in range(wall.size):
                    d = wall.distance(j, pos) - rad
                    cond *= d > 0
            if not cond:
                continue

            position[i, :] = pos
            i += 1

    def agent(self, size, three_circles_flag=True, body_type="adult"):
        """Arguments for constructing agent."""
        body = body_types[body_type]
        values = agent_table["value"]

        mass = self.truncnorm(loc=body["mass"], abs_scale=body["mass_scale"],
                              size=size)
        radius = self.truncnorm(loc=body["radius"], abs_scale=body["dr"],
                                size=size)
        r_t = body["k_t"] * radius    # radius_torso
        r_s = body["k_s"] * radius    # radius_shoulder
        r_ts = body["k_ts"] * radius  # distance_torso_shoulder

        # TODO: converters. Eval to values.
        pi = np.pi  # For eval
        inertia_rot = eval(values["inertia_rot"]) * np.ones(size)
        target_velocity = eval(values["target_velocity"]) * np.ones(size)
        target_angular_velocity = eval(values["target_angular_velocity"]) * np.ones(size)

        return size, mass, radius, r_t, r_s, r_ts, inertia_rot, \
               target_velocity, target_angular_velocity, three_circles_flag

    def round_wall(self, size, r_min, r_max):
        """Arguments for constructing round wall."""
        return np.stack((np.random.uniform(*self.x, size=size),
                         np.random.uniform(*self.y, size=size),
                         np.random.uniform(r_min, r_max, size=size)), axis=1)

    def linear_wall(self, size):
        """Arguments for constructing linear wall."""
        args = zip(self.random_2d_coordinates(size),
                   self.random_2d_coordinates(size))
        return np.array(tuple(args))
