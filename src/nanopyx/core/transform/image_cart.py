"""
Combination of functions for shifting an image, using several interpolation methods.
"""

import numpy as np

from ..utils.time.timeit import timeit2
from .interpolation import (
    bicubic,
    bilinear,
    nearest_neighbor,
    catmull_rom,
    lanczos,
)

@timeit2
def catmull_rom_cart(image: np.ndarray, x_shape: int, y_shape: int, scale:str='linear'):
    interpolator = catmull_rom.Interpolator(image)
    return interpolator.cartesian(x_shape,y_shape,scale)


@timeit2
def lanczos_cart(image: np.ndarray, x_shape: int, y_shape: int, scale:str='linear', taps: int = 3):
    interpolator = lanczos.Interpolator(image, taps)
    return interpolator.cartesian(x_shape,y_shape,scale)


@timeit2
def bicubic_cart(image: np.ndarray, x_shape: int, y_shape: int, scale:str='linear'):
    interpolator = bicubic.Interpolator(image)
    return interpolator.cartesian(x_shape,y_shape,scale)


@timeit2
def bilinear_cart(image: np.ndarray, x_shape: int, y_shape: int, scale:str='linear'):
    interpolator = bilinear.Interpolator(image)
    return interpolator.cartesian(x_shape,y_shape,scale)


@timeit2
def nearest_neighbor_cart(image: np.ndarray, x_shape: int, y_shape: int, scale:str='linear'):
    interpolator = nearest_neighbor.Interpolator(image)
    return interpolator.cartesian(x_shape,y_shape,scale)


