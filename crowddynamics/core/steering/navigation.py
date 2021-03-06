"""Navigation/path-planning algorithms

Continuos shortest path problem

Fast Marching Method.

https://github.com/scikit-fmm/scikit-fmm

Fast Iterative Method

https://github.com/SCIInstitute/SCI-Solver_Eikonal


"""
from collections import Iterable

import numba
import numpy as np
import skfmm
import skimage.draw
from shapely.geometry import LineString, Polygon
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from crowddynamics.core.geometry import shapes_to_point_pairs


def to_indices(points, step):
    """To indices

    Args:
        points (numpy.ndarray):
            Points on a continuous grid

        step (float):
            Step size of the grid

    Returns:
        np.ndarray:
            Array of integers. Indices of a point in discrete grid.

    """
    return np.round(points / step).astype(np.int64)


def set_values_to_grid(grid, step, shape, value):
    """Set values on discrete grid using ``scikit-image``.

    Args:
        shape (BaseGeometry):
            Shapely shape

        grid (numpy.ndarray):
            Grid to set values

        value (grid.dtype):
            Value to set to the grid points

        step (float):
            Step size of the grid

    Returns:
        None. Values are set to grid.
    """
    if isinstance(shape, Point):
        pass
    elif isinstance(shape, LineString):
        points = shapes_to_point_pairs(shape)
        points = to_indices(points, step)
        for args in points:
            j, i = skimage.draw.line(*args.flatten())
            grid[i, j] = value
    elif isinstance(shape, Polygon):
        points = np.asarray(shape.exterior)
        points = to_indices(points, step)
        x, y = points[:, 0], points[:, 1]
        j, i = skimage.draw.polygon(x, y)
        grid[i, j] = value
    elif isinstance(shape, Iterable):
        for shape_ in shape:
            set_values_to_grid(grid, step, shape_, value)


def meshgrid(step, minx, miny, maxx, maxy):
    """2-Dimensional meshgrid with inclusive end points ``maxx`` and ``maxy``.

    Returns:
        numpy.ndarray:
    """
    # TODO: matrix indexing='ij'
    x = np.arange(minx, maxx + step, step=step)
    y = np.arange(miny, maxy + step, step=step)
    return np.meshgrid(x, y, indexing='xy')


def distance_map(domain, targets, obstacles, step):
    r"""Distance map

    Distance map :math:`S(\mathbf{x})` is obtained by solving *Eikonal equation*
    using fast marching *Fast Marching Method (FMM)* (``scikit-fmm``).

    .. math::
       \left \| \nabla S(\mathbf{x}) \right \| = \frac{1}{f(\mathbf{x})}, \quad \mathbf{x} \in \Omega

    where

    - Function :math:`f : \bar{\Omega} \mapsto (0, +\infty)` is the speed of
      travel at :math:`\mathbf{x}`

    Boundary conditions for the distance map

    .. math::
       \begin{cases}
       S(\mathbf{x}) = 0, & \mathbf{x} \in \mathcal{E} \\
       S(\mathbf{x}) \to \infty, & \mathbf{x} \in \mathcal{O}
       \end{cases}

    Initial values for speed

    .. math::
       \begin{cases}
       f(\mathbf{x}) = 1, & \mathbf{x} \in \Omega \setminus \mathcal{O} \\
       f(\mathbf{x}) \to 0, & \mathbf{x} \in \mathcal{O}
       \end{cases}

    Args:
        domain (Polygon):
            Domain :math:`\Omega` containing obstacles and targets.

        obstacles (shapely.geometry.base.BaseGeometry, optional):
            Impassable regions :math:`\mathcal{O}` in the domain.

        targets (shapely.geometry.base.BaseGeometry, optional):
            Target regions :math:`\mathcal{E}` in the domain.

        step (float):
            - Positive float
            - Step size for the meshgrid.
            - Reference value :math:`0.01\,\mathrm{m}`.

    Return:
        (numpy.ndarray, numpy.ndarray, numpy.ma.MaskedArray):
            List of
            - ``mgrid``
            - ``dmap``
            - ``phi``
    """
    mgrid = meshgrid(step, *domain.bounds)

    # Numerical values for objects in the domain
    empty_region = -1.0
    target_region = 1.0
    obstacle_region = True
    non_obstacle_region = False

    # Contour used for solving distance map
    # Mask for masked values that represent obstacles for the solver
    contour = np.full_like(mgrid[0], empty_region, dtype=np.float64)
    mask = np.full_like(mgrid[0], non_obstacle_region, dtype=np.bool_)

    set_values_to_grid(contour, step, targets, target_region)
    set_values_to_grid(mask, step, obstacles, obstacle_region)

    # Solve distance map using Fast-Marching Method (FMM)
    phi = np.ma.MaskedArray(contour, mask)
    dmap = skfmm.distance(phi, dx=step)
    return mgrid, dmap, phi


def travel_time_map(step, domain, targets, obstacles, agents):
    r"""
    Dynamics potential takes into account the positions of the agents in the
    field. Equation

    .. math::
       \left \| \nabla T(\mathbf{x}) \right \| = \frac{1}{f(\mathbf{x})}, \quad \mathbf{x} \in \Omega

    and boundary conditions

    .. math::
       f(\mathbf{x}) &= 1, \quad \mathbf{x} \in \Omega \setminus (\mathcal{O} \cup \mathcal{A}) \\
       f(\mathbf{x}) &\leq 1, \quad \mathbf{x} \in \mathcal{A} \\
       f(\mathbf{x}) &\to 0, \quad \mathbf{x} \in \mathcal{O}

    .. math::
       \frac{1}{f(\mathbf{x})} = 1 + \max \left( 0, c_{0} \left( 1 + c_{1} \frac{\mathbf{v} \cdot \nabla S(\mathbf{x})}{v_{0} \| \nabla S(\mathbf{x}) \|} \right) \right)

    - :math:`c_{0} > 0` general impact strength
    - :math:`c_{1} > 0` impact of the moving direction of an agent

    Args:
        step (float):
            Step size for the meshgrid.

        domain (Polygon):
            Domain :math:`\Omega` containing obstacles and targets.

        obstacles (LineString, optional):
            Impassable regions :math:`\mathcal{O}` in the domain.

        targets (LineString, optional):
            Target regions :math:`\mathcal{E}` in the domain.

        agents:
            Regions occupied by agents :math:`\mathcal{A}`

    Returns:
        (numpy.meshgrid, numpy.ndarray, numpy.ma.MaskedArray):
    """
    return NotImplementedError


def direction_map(dmap):
    r"""
    Normalized gradient of distance map.

    .. math::
       \hat{\mathbf{e}}_{S} = -\frac{\nabla S(\mathbf{x})}{\| \nabla S(\mathbf{x}) \|}

    Args:
        dmap (numpy.ndarray):
            Distance map.

    Returns:
        numpy.ndarray:
            Direction map. Array of shape: ``dmap.shape + (2,)``

    """
    u, v = np.gradient(dmap)
    l = np.hypot(u, v)
    l[l == 0] = 1.0  # Handles l == 0 to avoid zero division
    # Flip order from (row, col) to (x, y)
    dir_map = np.zeros(u.shape + (2,))
    dir_map[:, :, 0] = v / l
    dir_map[:, :, 1] = u / l
    return dir_map


@numba.jit(nopython=True)
def merge_dir_maps(dmap, dir_map1, dir_map2, radius, value):
    r"""
    Function that merges two direction maps together. Let distance map from
    obstacles be :math:`\Phi(\mathbf{x})` and :math:`\lambda(\Phi(\mathbf{x}))`
    be any decreasing function :math:`\lambda^{\prime}(\Phi(\mathbf{x})) < 0` of
    distance from obstacles such that

    .. math::
       \lambda(\Phi) &=
       \begin{cases}
       1 & \Phi = 0 \\
       0 & \Phi > M > 0
       \end{cases}

    Then merged direction map :math:`\hat{\mathbf{e}}_{merged}` is

    .. math::
       k &= \lambda(\Phi(\mathbf{x})) \\
       \hat{\mathbf{e}}_{merged} &= k \hat{\mathbf{e}}_{obs} + (1 - k) \hat{\mathbf{e}}_{exits}

    Args:
        dmap:
        dir_map1:
        dir_map2:
        radius (float):
            Radius
        value (float):
            Value between (0, 1). Value denoting the strength of dir_map1 at
            distance of radius.

    Returns:
        numpy.ndarray:

    """
    n, m = dmap.shape
    merged = np.copy(dir_map2)
    for i in range(n):
        for j in range(m):
            x = np.abs(dmap[i, j])

            if x < 1.1 * radius:
                k = value ** (x / radius)  # Decreasing function
                merged[i, j] = - k * dir_map1[i, j] + (1 - k) * dir_map2[i, j]
    return merged


def static_potential(step, domain, targets, obstacles, radius, value):
    r"""
    Static potential is navigation algorithm that does not take into account
    the space that is occupied by dynamic agents (aka agents).

    Args:
        step (float):
        domain (Polygon):
        targets (LineString, optional):
        obstacles (LineString, optional):
        value (float):
        radius (float):

    Returns:
        numpy.ndarray:
    """
    # TODO: interpolation
    _, dmap_exits, _ = distance_map(domain, targets, obstacles, step)
    _, dmap_obs, _ = distance_map(domain, obstacles, None, step)

    dir_map_exits = direction_map(dmap_exits)
    dir_map_obs = direction_map(dmap_obs)

    dir_map = merge_dir_maps(dmap_obs, dir_map_obs, dir_map_exits, radius, value)

    return dir_map


def dynamic_potential():
    r"""
    Dynamic potential is navigation algorithm that takes into account the space
    that is occupied by dynamic agents (aka agents).
    """
    return NotImplementedError
