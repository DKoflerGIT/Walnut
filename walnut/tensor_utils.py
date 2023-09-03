"""Tensor utils module"""

import pandas as pd
import numpy as np
from walnut.tensor import Tensor, ShapeLike, AxisLike, ShapeError


__all__ = [
    "df_to_tensor",
    "expand_dims",
    "match_dims",
    "arange",
    "linspace",
    "zeros",
    "ones",
    "zeros_like",
    "ones_like",
    "randn",
    "randu",
    "randint",
    "shuffle",
    "check_dims",
    "choice",
    "empty",
    "maximum",
    "random_seed",
]


def df_to_tensor(df: pd.DataFrame) -> Tensor:
    """Converts a Pandas DataFrame into a Tensor.

    Parameters
    ----------
    df : pd.DataFrame
        Pandas DataFrame object to convert.

    Returns
    -------
    Tensor
        Tensor object.
    """
    return Tensor(df.to_numpy())


def expand_dims(x: Tensor, axis: AxisLike) -> Tensor:
    """Extends the dimensions of a tensor.

    Parameters
    ----------
    x : Tensor
        Tensor whose dimensions are to be extended.
    axis : AxisLike
        Where to insert the new dimension.

    Returns
    -------
    Tensor
        Tensor with extended dimensions.
    """
    return Tensor(np.expand_dims(x.data, axis=axis), dtype=x.dtype)


def match_dims(x: Tensor, dims: int) -> Tensor:
    """Extends the dimensions of a tensor to fit a given number of dims.

    Parameters
    ----------
    x : Tensor
        Tensor to be extended.
    dims : int
        Number of dimensions needed.

    Returns
    -------
    Tensor
        Tensor with extended dimensions.
    """
    while x.ndim < dims:
        x = expand_dims(x, axis=(-1,))

    return x


def arange(stop: int, start: int = 0, step: int | float = 1) -> Tensor:
    """Returns a 1d tensor with evenly spaced values samples,
    calculated over the interval [start, stop).

    Parameters
    ----------
    start : float
        Start value.
    stop : float
        Stop value.
    step : int | float, optional
        Spacing between values, by default 1.

    Returns
    -------
    Tensor
        1d tensor of evenly spaced samples.
    """
    x = np.arange(start, stop, step)
    return Tensor(x, dtype=str(x.dtype))


def linspace(start: float, stop: float, num: int) -> Tensor:
    """Returns a 1d tensor num evenly spaced samples, calculated over the interval [start, stop].

    Parameters
    ----------
    start : float
        Start value.
    stop : float
        Stop value.
    num : int
        Number of samples.

    Returns
    -------
    Tensor
        1d tensor of evenly spaced samples.
    """
    return Tensor(np.linspace(start, stop, num))


def zeros(shape: ShapeLike) -> Tensor:
    """Creates a tensor of a given shape with all values being zero.

    Parameters
    ----------
    ShapeLike
        Shape of the new tensor.

    Returns
    -------
    Tensor
        Tensor with all values being zero.
    """
    return Tensor(np.zeros(shape))


def ones(shape: ShapeLike) -> Tensor:
    """Creates a tensor of a given shape with all values being one.

    Parameters
    ----------
    ShapeLike
        Shape of the new tensor.

    Returns
    -------
    Tensor
        Tensor with all values being one.
    """
    return Tensor(np.ones(shape))


def zeros_like(x: Tensor) -> Tensor:
    """Creates a tensor based on the shape of a given other tensor with all values being zero.

    Parameters
    ----------
    x : Tensor
        Tensor whose shape is used.

    Returns
    -------
    Tensor
        Tensor with all values being zero.
    """
    return Tensor(np.zeros_like(x.data))


def ones_like(x: Tensor) -> Tensor:
    """Creates a tensor based on the shape of a given other tensor with all values being one.

    Parameters
    ----------
    x : Tensor
        Tensor whose shape is used.

    Returns
    -------
    Tensor
        Tensor with all values being one.
    """
    return Tensor(np.ones_like(x.data))


def randn(shape: ShapeLike, mean: float = 0.0, std: float = 1.0) -> Tensor:
    """Creates a tensor of a given shape with random values following a normal distribution.

    Parameters
    ----------
    ShapeLike
        Shape of the new tensor.
    mean : float, optional
        Mean of random values, by default 0.
    std : float, optional
        Standard deviation of random values, by default 1.

    Returns
    -------
    Tensor
        Tensor with random values.
    """
    return Tensor(np.random.normal(mean, std, shape))


def randu(shape: ShapeLike, low: float = 0.0, high: float = 1.0) -> Tensor:
    """Creates a tensor of a given shape with random values following a uniform distribution.

    Parameters
    ----------
    ShapeLike
        Shape of the new tensor.
    low : float, optional
        Lower bound for random values, by default 0.
    high : float, optional
        Upper bound for random values, by default 1.

    Returns
    -------
    Tensor
        Tensor with random values.
    """
    return Tensor(np.random.uniform(low, high, shape))


def randint(shape: ShapeLike, low: int, high: int) -> Tensor:
    """Creates a tensor of a given shape with random integer values.

    Parameters
    ----------
    ShapeLike
        Shape of the new tensor.
    low : int
        Lower bound for random values.
    high : int
        Upper bound for random values.

    Returns
    -------
    Tensor
        Tensor with random values.
    """
    return Tensor(np.random.randint(low, high, shape), dtype="int")


def shuffle(x: Tensor, y: Tensor) -> tuple[Tensor, Tensor]:
    """Shuffles two tensors equally along axis 0.

    Parameters
    ----------
    x : Tensor
        First tensor to be shuffled.
    y : Tensor
        Second tensor to be shuffled.

    Returns
    -------
    tuple[Tensor, Tensor]
        Shuffled tensors.

    Raises
    ------
    ShapeError
        If tensors are not of equal size along a axis 0
    """
    if x.len != y.len:
        raise ShapeError("Tensors must have equal lengths along axis 0")

    shuffle_index = np.random.permutation(x.len)
    return x[shuffle_index], y[shuffle_index]


def check_dims(x: Tensor, target_dim: int) -> None:
    """Checks if a tensors dimensions match desired target dimensions.

    Parameters
    ----------
    x : Tensor
        Tensor whose dimensions are checked.
    target_dim : int
        Number of dimension the tensor should have.

    Raises
    ------
    ShapeError
        If the tensor's dimensions do not match the target dimensions.
    """
    if x.ndim != target_dim:
        raise ShapeError("Input dimensions do not match.")


def choice(x: Tensor, num_samples: int = 1) -> Tensor:
    """Returns a random index based on a probability distribution tensor.

    Parameters
    ----------
    x : Tensor
        Tensor containing a probablitity distribution.
    num_samples : int, optional
        Number of samples drawn, by default 1.

    Returns
    -------
    Tensor
        Chosen samples.
    """
    arange = np.arange(x.flatten().len)
    samples = np.random.choice(arange, size=num_samples, p=x.data.flatten())
    return Tensor(samples, dtype="int")


def empty(dtype: str = "float32") -> Tensor:
    """Return an empty tensor.

    Parameters
    ----------
    dtype: str, optional
        Datatype of the tensor data, by default float32.
    Returns
    -------
    Tensor
        Empty tensor.
    """
    return Tensor(np.empty(0, dtype=dtype))


def maximum(a: Tensor | float | int, b: Tensor | float | int) -> Tensor:
    """Element-wise maximum of two tensors.

    Parameters
    ----------
    a : Tensor | float | int
        First tensor.
    b : Tensor | float | int
        Second value.

    Returns
    -------
    Tensor
        Tensor containing the element-wise maximum of either tensor.
    """
    _a = a.data if isinstance(a, Tensor) else a
    _b = b.data if isinstance(b, Tensor) else b
    return Tensor(np.maximum(_a, _b))


def stretch(
    x: Tensor,
    streching: tuple[int, int],
    target_shape: ShapeLike,
    axis: tuple[int, int] = (-2, -1),
) -> Tensor:
    """Strtches a tensor by repeating it's elements over given axis.

    Parameters
    ----------
    x : Tensor
        Tensor to be stretched out.
    streching : tuple[int, int]
        Number of repeating values along each axis.
    target_shape : ShapeLike
        Shape of the target tensor. If the shape does not match after stretching,
        remaining values are filled with zeroes.
    axis : tuple[int, int], optional
        Axis along which to stretch the tensor, by default (-2, -1).

    Returns
    -------
    Tensor
        Stretched out tensor.
    """
    fa1, fa2 = streching
    ax1, ax2 = axis
    x_stretched = np.repeat(x.data, fa1, axis=ax1)
    x_stretched = np.repeat(x_stretched, fa2, axis=ax2)
    # resize to fit target shape by filling with zeros
    return Tensor(np.resize(x_stretched, target_shape))


def random_seed(seed: int):
    """Sets the seed for RNG for reproducability.

    Parameters
    ----------
    seed : int
        Seed value.
    """
    np.random.seed(seed)
