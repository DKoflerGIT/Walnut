"""Neural network functions module"""

from typing import Callable, Literal, Optional
from ..preprocessing.basic import one_hot_encode
from ..tensor_f import arange, maximum, minimum, zeros
from ..tensor import Tensor, ShapeError
from ..types import AxisLike, ShapeLike


__all__ = [
    "relu",
    "leaky_relu",
    "gelu",
    "sigmoid",
    "softmax",
    "convolve1d",
    "convolve2d",
]
PI: float = 3.141592653589793
GELU_S: float = 0.7978845608028654  # sqrt(2/pi)
GELU_C: float = 0.044715


def relu(
    x: Tensor, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Applies the Rectified Linear Unit function.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    y = maximum(x, 0)

    backward = (lambda dy: (y > 0) * dy) if return_backward_fn else None
    return y, backward


def leaky_relu(
    x: Tensor, alpha: float = 0.01, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Applies the leaky ReLU function.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    alpha : float
        Slope of the negative output.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    x = x.float()
    y = maximum(x, 0) + alpha * minimum(0, x)
    backward = (
        (lambda dy: ((y > 0).float() + (y < 0).float() * alpha) * dy)
        if return_backward_fn
        else None
    )
    return y, backward


def gelu(
    x: Tensor, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Applies the Gaussian Error Linear Unit function.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """

    tmp = GELU_S * (x + GELU_C * x**3)
    y = 0.5 * x * (1 + tmp.tanh())
    backward = (
        (
            lambda dy: (
                0.5 * (1 + tmp.tanh())
                + 0.5 * x * tmp.sech() ** 2 * GELU_S * (1 + 3 * GELU_C * x**2)
            )
            * dy
        )
        if return_backward_fn
        else None
    )

    return y, backward


def sigmoid(
    x: Tensor, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Applies the sigmoid function.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    y = x.exp() * (1 + x.exp()) ** -1
    backward = (lambda dy: (y * (1 - y)) * dy) if return_backward_fn else None
    return y, backward


def tanh(
    x: Tensor, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Applies the hyperbolic tangent function.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    y = x.tanh()
    backward = (lambda dy: (1 - y**2) * dy) if return_backward_fn else None
    return y, backward


def softmax(x: Tensor, axis: AxisLike = -1) -> Tensor:
    """Applies the softmax function over a given axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    axis: AxisLike, optional
        Axis over which to compute the softmax, by default -1.

    Returns
    -------
    Tensor
        Output tensor.
    """
    x = (x - x.max(axis=axis, keepdims=True)).exp()
    return x / x.sum(axis=axis, keepdims=True)


def log_softmax(x: Tensor, axis: AxisLike = -1) -> Tensor:
    """Applies the log softmax function to the last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    axis: AxisLike, optional
        Axis over which to compute the softmax, by default -1.

    Returns
    -------
    Tensor
        Output tensor.
    """
    x = (x - x.max(axis=axis, keepdims=True)).exp()
    return (x / x.sum(axis=axis, keepdims=True)).log()


def temperature_softmax(x: Tensor, temperature: float = 1, axis: AxisLike = -1) -> Tensor:
    """Applies the softmax function with temperature to the last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    temperature : float, optional
        Temperature scaling to be applied in the calculation.
    axis: AxisLike, optional
        Axis over which to compute the softmax, by default -1.

    Returns
    -------
    Tensor
        Output tensor.
    """
    if temperature == 0:
        raise ValueError("Temperature cannot be 0.")

    x = ((x - x.max(axis=axis, keepdims=True)) / temperature).exp()
    return x / x.sum(axis=axis, keepdims=True)


def linear(
    x: Tensor, w: Tensor, b: Optional[Tensor] = None, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], tuple[Tensor, Optional[Tensor], Optional[Tensor]]]]]:
    """Applies the linear transformation X @ W^T + b.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    w : Tensor
        Weight tensor.
    b : Tensor, optional
        Bias tensor, by default None
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Linearly transformed tensor.
    Callable[[Tensor], tuple[Tensor, Tensor, Optional[Tensor]]], optional
        Backward function.
    """

    # (B, ... , Ci) @ (Ci, Co) -> (B, ..., Co)
    y = x @ w.T
    if b is not None:
        y += b

    if return_backward_fn:

        def backward(dy: Tensor) -> tuple[Tensor, Optional[Tensor], Optional[Tensor]]:
            # input grads
            # (B, ... , Co) @ (Co, Ci) -> (B, ..., Ci)
            dx = dy @ w

            # weight grads
            if w.requires_grad:
                # 2D: (Co, B) @ (B, Ci) -> (Co, Ci)
                # ND: (B, ..., Co, Bn) @ (B, ... , Bn, Ci) -> (B, ..., Co, Ci)
                dw = dy.T @ x
                if x.ndim > 2:
                    # sum over all batch dimensions
                    # (B, ..., Ci, Co) -> (Ci, Co)
                    axes = tuple(range(x.ndim - 2))
                    dw = dw.sum(axis=axes)
            else:
                dw = None

            # bias grads
            if b is not None and b.requires_grad:
                # sum over all batch dimensions
                # (B, ... , Co) -> (Co,)
                axes = tuple(range(x.ndim - 1))
                db = dy.sum(axis=axes)
            else:
                db = None

            return dx, dw, db

        return y, backward

    return y, None


def convolve1d(
    x: Tensor,
    f: Tensor,
    padding: Literal["causal", "full", "same", "valid"] = "valid",
    stride: int = 1,
    dilation: int = 1,
) -> Tensor:
    """Convolves two tensors over their last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    f : Tensor
        Filter tensor.
    padding: Literal["causal", "full", "same", "valid"], optional
        Padding applied to a tensor before the convolution, by default "causal".
    stride : int, optional
        Stride used in the convolution operation, by default 1.
    dilation : int, optional
        Dilation used for each axis of the filter, by default 1.
    Returns
    -------
    Tensor
        Output tensor.

    Raises
    -------
    ShapeError
        If dimensions of input and filter do not match.
    """
    if x.ndim != f.ndim:
        raise ShapeError("Dimensions of input and filter must match.")

    if dilation > 1:
        f = __dilate1d(f, dilation)

    if padding != "valid":
        p = __pad1d_from_str(padding, f.shape[-1])
        x = __pad1d(x, p)

    return __convolve1d(x, f, stride)


def __pad1d_from_str(
    padding: Literal["causal", "full", "same", "valid"], kernel_size: int
) -> tuple[int, int]:
    match padding:
        case "causal":
            return (kernel_size - 1, 0)
        case "full":
            return (kernel_size - 1,) * 2
        case "same":
            return (kernel_size // 2,) * 2
        case _:
            return (0, 0)


def __pad1d(x: Tensor, padding: tuple[int, int]) -> Tensor:
    widths = tuple([(0, 0)] * (x.ndim - 1) + [padding])
    return x.pad(widths)


def __dilate1d(x: Tensor, dilation: int) -> Tensor:
    if dilation == 1:
        return x

    dilated_shape = (dilation * x.shape[-1] - 1,)
    x_dilated = zeros(x.shape[:-1] + dilated_shape, x.dtype, x.device)
    dilation_slice = [slice(None)] * (x.ndim - 1) + [slice(None, None, dilation)]
    x_dilated[*dilation_slice] = x
    return x_dilated


def __convolve1d(x: Tensor, f: Tensor, stride: int = 1) -> Tensor:
    # convolution
    cdtype = "complex64"
    conv = (
        (x.fft1d(dtype=cdtype) * f.fft1d(n=x.shape[-1], dtype=cdtype))
        .ifft1d(dtype=cdtype)
        .real(dtype=x.dtype)
    )

    # slicing
    out = x.shape[-1] - f.shape[-1] + 1
    out_slice = [slice(None)] * (x.ndim - 1) + [slice(-out, None)]
    stride_slice = [slice(None)] * (x.ndim - 1) + [slice(None, None, stride)]

    return conv[*out_slice][*stride_slice]


def convolve2d(
    x: Tensor,
    f: Tensor,
    padding: Literal["same", "valid"] = "valid",
    stride: int = 1,
    dilation: int = 1,
) -> Tensor:
    """Convolves two tensors over their last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    f : Tensor
        Filter tensor.
    padding: Literal["same", "valid"], optional
        Padding applied to a tensor before the convolution, by default "valid".
    stride : int, optional
        Stride used in the convolution operation, by default 1.
    dilation : int, optional
        Dilation used for each axis of the filter, by default 1.

    Returns
    -------
    Tensor
        Output tensor.

    Raises
    -------
    ShapeError
        If dimensions of input and filter do not match.
    """
    if x.ndim != f.ndim:
        raise ShapeError("Dimensions of input and filter must match.")

    if dilation > 1:
        f = __dilate2d(f, (dilation, dilation))

    if padding != "valid":
        p = __pad2d_from_str(padding, f.shape[-1])
        x = __pad2d(x, p)

    return __convolve2d(x, f, (stride, stride))


def __pad2d_from_str(padding: Literal["same", "valid"], kernel_size: int):
    match padding:
        case "full":
            return ((kernel_size - 1,) * 2,) * 2
        case "same":
            return ((kernel_size // 2,) * 2,) * 2
        case _:
            return ((0, 0), (0, 0))


def __pad2d(x: Tensor, padding: tuple[tuple[int, int]]) -> Tensor:
    widths = tuple([(0, 0)] * (x.ndim - 2) + [*padding])
    return x.pad(widths)


def __dilate2d(x: Tensor, dilation: tuple[int, int]) -> Tensor:
    dilated_shape = (
        dilation[0] * x.shape[-2] - 1,
        dilation[1] * x.shape[-1] - 1,
    )
    x_dilated = zeros(x.shape[:-2] + dilated_shape, x.dtype, x.device)
    dilation_slice = (
        [slice(None)] * (x.ndim - 2)
        + [slice(None, None, dilation[0])]
        + [slice(None, None, dilation[1])]
    )
    x_dilated[*dilation_slice] = x
    return x_dilated


def __convolve2d(
    x: Tensor,
    f: Tensor,
    strides: tuple[int, int] = (1, 1),
) -> Tensor:
    # convolution
    cdtype = "complex64"
    conv = (
        (x.fft2d(dtype=cdtype) * f.fft2d(s=x.shape[-2:], dtype=cdtype))
        .ifft2d(dtype=cdtype)
        .real(dtype=x.dtype)
    )

    # slicing
    out_y = x.shape[-2] - f.shape[-2] + 1
    out_x = x.shape[-1] - f.shape[-1] + 1
    out_slice = [slice(None)] * (x.ndim - 2) + [
        slice(-out_y, None),
        slice(-out_x, None),
    ]
    stride_slice = [slice(None)] * (x.ndim - 2) + [
        slice(None, None, strides[0]),
        slice(None, None, strides[1]),
    ]

    return conv[*out_slice][*stride_slice]


def upsample2d(
    x: Tensor,
    scaling_factors: tuple[int, int],
    shape: ShapeLike,
    axes: tuple[int, int] = (-2, -1),
) -> Tensor:
    """Upsamples a tensor by repeating it's elements over given axes.

    Parameters
    ----------
    x : Tensor
        Tensor to be stretched out.
    scaling_factors : tuple[int, int]
        Number of repeating values along each axis.
    shape : ShapeLike
        Shape of the target tensor. If the shape does not match after stretching,
        remaining values are filled with zeroes.
    axes : tuple[int, int], optional
        Axes along which to stretch the tensor, by default (-2, -1).

    Returns
    -------
    Tensor
        Upsampled tensor.
    """
    sf1, sf2 = scaling_factors
    ax1, ax2 = axes
    x_str = x.repeat(sf1, ax1).repeat(sf2, ax2)
    return x_str if x_str.shape == shape else x_str.pad_to_shape(shape)


def maxpooling2d(
    x: Tensor, kernel_size: tuple[int, int] = (2, 2), return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Performs a max pooling over the last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    kernel_size : tuple[int, int], optional
        Size of the pooling window, by default (2, 2).
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    B, C, Yi, Xi = x.shape
    Ky, Kx = kernel_size

    # maxpooling
    x_crop = x[:, :, : Yi // Ky * Ky, : Xi // Kx * Kx]
    y = x_crop.reshape((B, C, Yi // Ky, Ky, Xi // Kx, Kx)).max(axis=(-3, -1))

    if return_backward_fn:
        y_ups = upsample2d(y, kernel_size, x.shape)
        backward = (
            (lambda dy: upsample2d(dy, kernel_size, x.shape) * (x == y_ups).int())
            if return_backward_fn
            else None
        )
        return y, backward

    return y, None


def avgpooling2d(
    x: Tensor, kernel_size: tuple[int, int] = (2, 2), return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Tensor]]]:
    """Performs a average pooling over the last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    kernel_size : tuple[int, int], optional
        Size of the pooling window, by default (2, 2).
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    B, C, Yi, Xi = x.shape
    Ky, Kx = kernel_size

    # avgpooling
    x_crop = x[:, :, : Yi // Ky * Ky, : Xi // Kx * Kx]
    y = x_crop.reshape((B, C, Yi // Ky, Ky, Xi // Kx, Kx)).mean(axis=(-3, -1))

    if return_backward_fn:
        backward = (
            (lambda dy: upsample2d(dy, kernel_size, x.shape) / (Ky * Kx))
            if return_backward_fn
            else None
        )
        return y, backward

    return y, None


def lookup_embedding(
    x: Tensor, embedding_table: Tensor, return_backward_fn: bool = False
) -> tuple[Tensor, Optional[Callable[[Tensor], Optional[Tensor]]]]:
    """Performs lookup embedding on a tensor.

    Parameters
    ----------
    x : Tensor
        Input tensor of integer dtype used for indexing into the embedding table.
    embedding_table : Tensor
        Tensor of embedding values.
    return_backward_fn: bool, optional
        Whether to also return the according backward function, by default False.

    Returns
    -------
    Tensor
        Output tensor.
    Callable[[Tensor], Tensor]], optional
        Backward function.
    """
    if x.dtype not in ("int32", "int64"):
        raise ValueError(f"Input must be int32 or int64, got {x.dtype}.")

    x = one_hot_encode(x, embedding_table.shape[0]).astype(embedding_table.dtype)
    y = x @ embedding_table

    if return_backward_fn:

        def backward(dy: Tensor) -> Optional[Tensor]:
            # embedding table grads
            if embedding_table.requires_grad:
                return (x.T @ dy).sum(axis=0)

        return y, backward

    return y, None
