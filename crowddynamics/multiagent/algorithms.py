import numpy as np

from crowddynamics.core.geometry import shapes_to_point_pairs
from crowddynamics.core.interactions import agent_agent_block_list, agent_wall
from crowddynamics.core.motion import force_fluctuation, \
    torque_fluctuation, force_adjust, torque_adjust
from crowddynamics.core.integrator import integrate
from crowddynamics.core.navigation import _to_indices, static_potential
from crowddynamics.core.vector2D import angle_nx2
from crowddynamics.functions import public, Timed
from crowddynamics.task_graph import TaskNode


@public
class Integrator(TaskNode):
    def __init__(self, simulation, dt):
        """

        :param simulation: Simulation class
        :param dt: Tuple of minumum and maximum timestep (dt_min, dt_max).
        """
        super().__init__()

        self.simulation = simulation
        self.dt = dt

        self.time_tot = np.float64(0)
        self.dt_prev = np.float64(np.nan)

    def update(self):
        """
        Integrates the system.

        Returns:
            None

        """
        self.dt_prev = integrate(self.simulation.agent, *self.dt)
        self.time_tot += self.dt_prev
        self.simulation.dt_prev = self.dt_prev
        self.simulation.time_tot += self.dt_prev


@public
class Fluctuation(TaskNode):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

    def update(self):
        agent = self.simulation.agent
        i = agent.indices()

        agent.force[i] = force_fluctuation(agent.mass[i], agent.std_rand_force)

        if agent.orientable:
            agent.torque[i] = torque_fluctuation(agent.inertia_rot[i],
                                                 agent.std_rand_torque)


@public
class Adjusting(TaskNode):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

    def update(self):
        agent = self.simulation.agent
        i = agent.indices

        agent.force[i] = force_adjust(agent.mass[i],
                                      agent.tau_adj,
                                      agent.target_velocity[i],
                                      agent.target_direction[i],
                                      agent.velocity[i])
        if agent.orientable:
            agent.torque[i] = torque_adjust(agent.inertia_rot[i],
                                            agent.tau_rot,
                                            agent.target_angle[i],
                                            agent.angle[i],
                                            agent.target_angle[i],
                                            agent.angular_velocity[i])


@public
class AgentAgentInteractions(TaskNode):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

    @Timed("Agent-Agent Interaction")
    def update(self):
        agent_agent_block_list(self.simulation.agent)


@public
class AgentObstacleInteractions(TaskNode):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

        # TODO: Expects that field is set prior to initialisation
        self.walls = shapes_to_point_pairs(self.simulation.obstacles)

    @Timed("Agent-Obstacle Interaction")
    def update(self):
        agent_wall(self.simulation.agent, self.walls)


@public
class Navigation(TaskNode):
    """
    Handles navigation in multi-agent simulation.
    """

    def __init__(self, simulation, algorithm="static", step=0.01):
        """

        Args:
            simulation:
            algorithm:
            step (float): Step size for the grid.

        """
        super().__init__()
        self.simulation = simulation

        self.step = step
        self.direction_map = None

        if algorithm == "static":
            self.direction_map = static_potential(self.step,
                                                  self.simulation.domain,
                                                  self.simulation.exits,
                                                  self.simulation.obstacles,
                                                  radius=0.3,
                                                  value=0.3)
        elif algorithm == "dynamic":
            raise NotImplementedError
        else:
            pass

    @Timed("Navigation Time")
    def update(self):
        """
        Changes target directions of active agents.

        Returns:
            None.

        """
        i = self.simulation.agent.indices()
        points = self.simulation.agent.position[i]
        # indices = self.points_to_indices(points)
        indices = _to_indices(points, self.step)
        indices = np.fliplr(indices)
        # http://docs.scipy.org/doc/numpy/reference/arrays.indexing.html
        # TODO: Handle index out of bounds -> numpy.take
        d = self.direction_map[indices[:, 0], indices[:, 1], :]
        self.simulation.agent.target_direction[i] = d


@public
class Orientation(TaskNode):
    """
    Target orientation
    """

    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

    @Timed("Orientation Time")
    def update(self):
        if self.simulation.agent.orientable:
            dir_to_orient = angle_nx2(self.simulation.agent.target_direction)
            self.simulation.agent.target_angle[:] = dir_to_orient


@public
class ExitSelection(TaskNode):
    """Exit selection policy."""

    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation

    def update(self):
        pass