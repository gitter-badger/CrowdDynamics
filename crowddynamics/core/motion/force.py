import numba
import numpy as np
from numba import f8
from scipy.stats import truncnorm

from crowddynamics.core.vector2D.vector2D import dot2d


def force_fluctuation(mass, scale):
    r"""
    Truncated normal distribution with standard deviation of 3.

    .. math::
       \boldsymbol{\xi} = \xi \cdot \mathbf{\hat{e}}(\varphi)

    where

    .. math::
       \xi \sim \mathcal{N}(\mu, \sigma^{2}) \\
       \varphi \sim \mathcal{U}(-\pi, \pi)

    Args:
        mass (float):
            Mass

        scale (float):
            Standard deviation of truncated normal distribution

    Returns:
        numpy.ndarray: Fluctuation force
    """
    if isinstance(mass, np.ndarray):
        size = len(mass)
    elif isinstance(scale, np.ndarray):
        size = len(scale)
    else:
        size = 1

    magnitude = truncnorm.rvs(0.0, 3.0, loc=0.0, scale=scale, size=size)
    angle = np.random.uniform(0.0, 2.0 * np.pi, size=size)
    force = magnitude * np.array((np.cos(angle), np.sin(angle)))
    return force.T * mass


@numba.jit(nopython=True, nogil=True)
def force_adjust(mass, tau_adj, v0, e0, v):
    r"""
    *Adjusting* aka *driving* force accounts of agent's desire to reach a
    certain destination. In high crowd densities term *manoeuvring* is used.
    Force affecting the agent takes form

    .. math::
       \mathbf{f}_{adj} = \frac{m}{\tau_{adj}} (v_{0} \mathbf{\hat{e}_{0}} - \mathbf{v}),

    Args:
        mass (float):
            Mass

        tau_adj (float):
            Characteristic time :math:`\tau_{adj}` time for agent to adjust it
            movement. Value :math:`0.5` is often used, but for example impatient
            agent that tend to push other agent more this value can be reduced.

        v0 (float):
            Target velocity :math:`v_{0}` is usually *average walking speed* for
            agent in its current situation.

        e0 (numpy.ndarray):
            Target direction :math:`\mathbf{\hat{e}_{0}}` is solved by
            *navigation* or *path planning* algorithm. More details in the
            navigation section.

        v (numpy.ndarray):
            Velocity

    Returns:
        numpy.ndarray:
    """
    return (mass / tau_adj) * (v0 * e0 - v)


@numba.jit(f8[:](f8, f8[:], f8, f8), nopython=True, nogil=True)
def force_social_helbing(h, n, a, b):
    r"""
    Helbing's model's original social force. Independent of the velocity or
    direction of the agent.

    .. math::
       A \exp(-h / B) \mathbf{\hat{n}}

    Args:
        h (float):
            Skin-to-skin distance between agents

        n (numpy.ndarray):
            Normal unit vector

        a (float):
            Constant :math:`A = 2 \cdot 10^{3} \,\mathrm{N}`

        b (float):
            Constant :math:`B = 0.08 \,\mathrm{m}`

    Returns:
        numpy.ndarray: Social force
    """
    return a * np.exp(- h / b) * n


@numba.jit(f8[:](f8, f8[:], f8[:], f8[:], f8, f8, f8), nopython=True,
           nogil=True)
def force_contact(h, n, v, t, mu, kappa, damping):
    r"""
    Physical contact force with damping. Helbing's original model did not
    include damping, which was added by Langston.

    .. math::
       \mathbf{f}^{c} = - h \cdot \left(\mu \cdot \hat{\mathbf{n}} -
       \kappa \cdot (\mathbf{v} \cdot \hat{\mathbf{t}}) \hat{\mathbf{t}}\right) +
       c_{n} \cdot (\mathbf{v} \cdot \hat{\mathbf{n}}) \hat{\mathbf{n}}

    Args:
        h (float):
            Skin-to-skin distance between agents

        n (numpy.ndarray):
            Normal vector

        v (numpy.ndarray):
            Velocity vector

        t (numpy.ndarray):
            Tangent vector

        mu (float):
            Constant :math:`1.2 \cdot 10^{5}\,\mathrm{kg\,s^{-2}}`

        kappa (float):
            Constant :math:`4.0 \cdot 10^{4}\,\mathrm{kg\,m^{-1}s^{-1}}`

        damping (float):
            Constant :math:`500 \,\mathrm{N}`

    Returns:
        numpy.ndarray: Contact force
    """
    return - h * (mu * n - kappa * dot2d(v, t) * t) + damping * dot2d(v, n) * n