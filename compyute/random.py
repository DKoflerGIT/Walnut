"""Random functions module"""

from contextlib import contextmanager
from typing import Iterator, Optional

from .base_tensor import Tensor, _ShapeLike, tensor
from .dtypes import _DtypeLike, dtype_to_str
from .engine import Device, _DeviceLike, get_engine

__all__ = [
    "normal",
    "uniform",
    "uniform_int",
    "permutation",
    "set_seed",
    "shuffle",
    "multinomial",
]


def set_seed(value: Optional[int] = None) -> None:
    """Sets the seed of the random number generator for reproducability.

    Parameters
    ----------
    value : int, optional
        Seed value.
    """
    try:
        get_engine(Device.CUDA).random.seed(value)
    except Exception:
        pass
    get_engine(Device.CPU).random.seed(value)


@contextmanager
def seed(value: Optional[int] = None) -> Iterator[None]:
    """Sets the seed of the random number generator for reproducability."""
    set_seed(value)
    try:
        yield
    finally:
        set_seed()


def normal(
    shape: _ShapeLike,
    mean: float = 0.0,
    std: float = 1.0,
    dtype: Optional[_DtypeLike] = None,
    device: _DeviceLike = Device.CPU,
) -> Tensor:
    """Returns a tensor with values drawn from a normal distribution.

    Parameters
    ----------
    _ShapeLike
        Shape of the new tensor.
    mean : float, optional
        Mean of random values, by default 0.
    std : float, optional
        Standard deviation of random values, by default 1.
    dtype: _DtypeLike, optional
        Datatype of the tensor data, by default None.
    device: _DeviceLike, optional
        The device the tensor is stored on, by default Device.CPU.

    Returns
    -------
    Tensor
        Tensor of normally distributed samples.
    """
    dtype = dtype_to_str(dtype) if dtype is not None else None
    return tensor(get_engine(device).random.normal(mean, std, shape), device=device, dtype=dtype)


def uniform(
    shape: _ShapeLike,
    low: float = -1.0,
    high: float = 1.0,
    dtype: Optional[_DtypeLike] = None,
    device: _DeviceLike = Device.CPU,
) -> Tensor:
    """Returns a tensor with values drawn from a uniform distribution.

    Parameters
    ----------
    _ShapeLike
        Shape of the new tensor.
    low : float, optional
        Lower bound for random values, by default 0.
    high : float, optional
        Upper bound for random values, by default 1.
    dtype: _DtypeLike, optional
        Datatype of the tensor data, by default None.
    device: _DeviceLike, optional
        The device the tensor is stored on, by default Device.CPU.

    Returns
    -------
    Tensor
        Tensor of uniformly distributed samples.
    """
    dtype = dtype_to_str(dtype) if dtype is not None else None
    return tensor(get_engine(device).random.uniform(low, high, shape), device=device, dtype=dtype)


def uniform_int(
    shape: _ShapeLike,
    low: int,
    high: int,
    dtype: Optional[_DtypeLike] = None,
    device: _DeviceLike = Device.CPU,
) -> Tensor:
    """Returns a tensor with integer values drawn from a discrete uniform distribution.

    Parameters
    ----------
    _ShapeLike
        Shape of the new tensor.
    low : int
        Lower bound for random values.
    high : int
        Upper bound for random values.
    dtype: _DtypeLike, optional
        Datatype of the tensor data, by default None.
    device: _DeviceLike, optional
        The device the tensor is stored on, by default Device.CPU.

    Returns
    -------
    Tensor
        Tensor of samples.
    """
    dtype = dtype_to_str(dtype) if dtype is not None else None
    return tensor(get_engine(device).random.randint(low, high, shape), device=device, dtype=dtype)


def permutation(
    n: int, dtype: Optional[_DtypeLike] = None, device: _DeviceLike = Device.CPU
) -> Tensor:
    """Returns a tensor containing a permuted range of length n.

    Parameters
    ----------
    n : int
        Length of the permuted range.
    dtype: _DtypeLike, optional
        Datatype of the tensor data, by default None.
    device: _DeviceLike, optional
        The device the tensor is stored on, by default Device.CPU.

    Returns
    -------
    Tensor
        Permuted tensor.
    """
    dtype = dtype_to_str(dtype) if dtype is not None else None
    return tensor(get_engine(device).random.permutation(n), device=device, dtype=dtype)


def multinomial(x: Tensor | int, p: Tensor, shape: _ShapeLike) -> Tensor:
    """Returns a tensor of values drawn from a given probability distribution tensor.

    Parameters
    ----------
    x : Tensor | int
        If a tensor, it represents possible values to draw.
        If an int, values are drawn from arange(x).
    p : Tensor
        Corresponding probablitity distribution.
    shape : _ShapeLike
        Shape of the new tensor.

    Returns
    -------
    Tensor
        Tensor of samples.
    """
    if isinstance(x, int):
        return Tensor(get_engine(p.device).random.choice(x, size=shape, p=p.data))
    return Tensor(get_engine(p.device).random.choice(x.data, size=shape, p=p.data))


def multinulli(p: float, shape: _ShapeLike, device: _DeviceLike = Device.CPU) -> Tensor:
    """Returns a tensor of repeated bernoulli experiments using a given probability.

    Parameters
    ----------
    p : float
        Probability of success.
    shape : _ShapeLike
        Shape of the new tensor.
    device: _DeviceLike, optional
        The device the tensor is stored on, by default Device.CPU.

    Returns
    -------
    Tensor
        Tensor of samples.
    """
    return Tensor(get_engine(device).random.choice([0, 1], size=shape, p=[p, 1 - p]))


def shuffle(x: Tensor) -> tuple[Tensor, Tensor]:
    """Shuffles a tensor along axis 0.

    Parameters
    ----------
    x : Tensor
        Tensor to be shuffled.

    Returns
    -------
    Tensor
        Shuffled tensor.
    Tensor
        Indices tensor.
    """
    shuffle_idx = permutation(x.shape[0], device=x.device)
    return x[shuffle_idx], shuffle_idx
