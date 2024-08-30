"""Neural network convolution functions."""

import math
from typing import Literal, Optional

from ...tensor_ops.creating import zeros
from ...tensor_ops.reshaping import (
    broadcast_to,
    flip,
    insert_dim,
    pad,
    pad_to_shape,
    repeat,
)
from ...tensor_ops.transforming import convolve1d_fft, convolve2d_fft
from ...tensor_ops.transforming import max as cp_max
from ...tensor_ops.transforming import mean
from ...tensor_ops.transforming import sum as cp_sum
from ...tensors import ShapeLike, Tensor
from .functions import Function, FunctionCache, PseudoCache

__all__ = [
    "convolve1d",
    "dilate1d",
    "pad1d",
    "convolve2d",
    "dilate2d",
    "pad2d",
    "upsample2d",
    "maxpooling2d",
    "avgpooling2d",
]

PaddingLike = Literal["valid", "same"]


class FConvolution1D(Function):
    """Computes the convolution of two tensors over their last axis."""

    @staticmethod
    def forward(
        cache: FunctionCache,
        x: Tensor,
        f: Tensor,
        b: Optional[Tensor],
        padding: PaddingLike,
        stride: int,
        dilation: int,
    ) -> Tensor:
        # dilate filter and add a fake batch dimension
        f = FDilation1D.forward(cache, f, dilation)
        f_ext = insert_dim(f, 0)  # (1, Co, Ci, F)

        # pad input and add a fake output dimension
        p = _pad1d_from_str(padding, f_ext.shape[-1])
        x = FPad1D.forward(cache, x, p)
        x_ext = insert_dim(x, 1)  # (B, 1, Ci, T)

        # perform convolution and sum over input dimension (B, Co, Ci, T)
        conv = _FConvolution1D.forward(cache, x_ext, f_ext, stride)
        y = cp_sum(conv, axis=2)  # (B, Co, T)

        if b:
            cache.b = b is not None
            y += insert_dim(b, -1)

        cache.conv_shape = conv.shape
        return y

    @staticmethod
    def backward(
        cache: FunctionCache, dy: Tensor
    ) -> tuple[Tensor, Tensor, Optional[Tensor]]:
        b, conv_shape = cache.b, cache.conv_shape

        # insert fake input channel dimension
        dy_ext = insert_dim(dy, 2)  # (B, Co, 1, X)
        dy_ext = broadcast_to(dy_ext, conv_shape)
        dx, df = _FConvolution1D.backward(cache, dy_ext)

        dx = FPad1D.backward(cache, cp_sum(dx, axis=1))
        df = FDilation1D.backward(cache, cp_sum(df, axis=0))
        db = cp_sum(dy, axis=(0, 2)) if b else None

        return dx, df, db


def convolve1d(
    x: Tensor,
    f: Tensor,
    b: Optional[Tensor] = None,
    padding: PaddingLike = "valid",
    stride: int = 1,
    dilation: int = 1,
) -> Tensor:
    """Computes the convolution of two tensors over their last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    f : Tensor
        Filter tensor.
    b : Tensor, optional
        Bias tensor. Defaults to ``None``. If ``None``, no bias is added.
    padding : PaddingLike, optional
        Padding applied to the input tensor. Defaults to ``valid``.
    stride : int, optional
        Stride used in the convolution operation. Defaults to ``1``.
    dilation : int, optional
        Dilation factor to use for each axis of the filter. Defaults to ``1``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.Convolution1d`
    """
    return FConvolution1D.forward(PseudoCache(), x, f, b, padding, stride, dilation)


class FDilation1D(Function):
    """Dilates a tensor in its last axis."""

    @staticmethod
    def forward(cache: FunctionCache, x: Tensor, dilation: int) -> Tensor:
        cache.no_dilation = dilation == 1
        if dilation == 1:
            return x

        dil_shape = (dilation * x.shape[-1] - 1,)
        y = zeros(x.shape[:-1] + dil_shape, x.device, x.dtype)
        y[..., ::dilation] = x

        cache.dilation = dilation
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        no_dilation, dilation = cache.no_dilation, cache.dilation
        if no_dilation:
            return dy
        return dy[..., ::dilation]


def dilate1d(x: Tensor, dilation: int) -> Tensor:
    """Dilates a tensor in its last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    dilation : int
        Dilation factor to use.

    Returns
    -------
    Tensor
        Output tensor.
    """
    return FDilation1D.forward(PseudoCache(), x, dilation)


class FPad1D(Function):
    """Pads a tensor in its last axis."""

    @staticmethod
    def forward(cache: FunctionCache, x: Tensor, padding: tuple[int, int]) -> Tensor:
        cache.no_padding = padding == (0, 0)
        if padding == (0, 0):
            return x
        widths = tuple([(0, 0)] * (x.n_axes - 1) + [padding])
        y = pad(x, widths)
        cache.padding = padding
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        no_padding, padding = cache.no_padding, cache.padding
        if no_padding:
            return dy
        return dy[..., padding[0] : -padding[0]]


def pad1d(x: Tensor, padding: tuple[int, int]) -> Tensor:
    """Pads a tensor in its last axis.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    padding : tuple[int, int]
        Padding width applied to the beginning and end of the last axis.

    Returns
    -------
    Tensor
        Output tensor.
    """
    return FPad1D.forward(PseudoCache(), x, padding)


def _pad1d_from_str(padding: PaddingLike, kernel_size: int) -> tuple[int, int]:
    if padding == "valid":
        return (0, 0)
    return (kernel_size // 2, kernel_size // 2)


class _FConvolution1D(Function):
    """Computes the 1D convolution of two tensors."""

    @staticmethod
    def forward(cache: FunctionCache, x: Tensor, f: Tensor, stride: int) -> Tensor:
        f_flipped = flip(f, -1)
        conv = convolve1d_fft(x, f_flipped)
        y = conv[..., ::stride]

        cache.x, cache.f, cache.stride, cache.conv_shape = x, f, stride, conv.shape
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor]:
        x, f, stride, conv_shape = cache.x, cache.f, cache.stride, cache.conv_shape

        # fill elements skipped by strides with zeros
        dy = dilate1d(dy, stride)
        dy = pad_to_shape(dy, conv_shape)

        dy = pad1d(dy, (f.shape[-1] - 1, f.shape[-1] - 1))  # full pad dy
        dx = convolve1d_fft(dy, f)

        dy = flip(dy, axis=-1)
        df = convolve1d_fft(dy, x)

        return dx, df


class FConvolution2D(Function):
    """Computes the convolution of two tensors over their last axis."""

    @staticmethod
    def forward(
        cache: FunctionCache,
        x: Tensor,
        f: Tensor,
        b: Optional[Tensor],
        padding: PaddingLike,
        stride: int,
        dilation: int,
    ) -> Tensor:
        # dilate filter and add a fake batch dimension
        f = FDilation2D.forward(cache, f, (dilation, dilation))
        f_ext = insert_dim(f, 0)  # (1, Co, Ci, Fy, Fx)

        # pad input and add a fake output dimension
        p = _pad2d_from_str(padding, f_ext.shape[-1])
        x = FPad2D.forward(cache, x, p)
        x_ext = insert_dim(x, 1)  # (B, 1, Ci, Y, X)

        # perform convolution and sum over input dimension (B, Co, Ci, T)
        conv = _FConvolution2D.forward(cache, x_ext, f_ext, (stride, stride))
        y = cp_sum(conv, axis=2)  # (B, Co, Y, X)

        if b:
            cache.b = b is not None
            y += b.to_shape((*b.shape, 1, 1))

        cache.conv_shape = conv.shape
        return y

    @staticmethod
    def backward(
        cache: FunctionCache, dy: Tensor
    ) -> tuple[Tensor, Tensor, Optional[Tensor]]:
        b, conv_shape = cache.b, cache.conv_shape

        # insert fake input channel dimension
        dy_ext = insert_dim(dy, 2)  # (B, Co, 1, X)
        dy_ext = broadcast_to(dy_ext, conv_shape)
        dx, df = _FConvolution2D.backward(cache, dy_ext)

        dx = FPad2D.backward(cache, cp_sum(dx, axis=1))
        df = FDilation2D.backward(cache, cp_sum(df, axis=0))
        db = cp_sum(dy, axis=(0, 2, 3)) if b else None

        return dx, df, db


def convolve2d(
    x: Tensor,
    f: Tensor,
    b: Optional[Tensor] = None,
    padding: PaddingLike = "valid",
    stride: int = 1,
    dilation: int = 1,
) -> Tensor:
    """Computes the convolution of two tensors over their last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    f : Tensor
        Filter tensor.
    b : Tensor, optional
        Bias tensor. Defaults to ``None. If ``None``, no bias is added.
    padding : PaddingLike, optional
        Padding applied to the input tensor. Defaults to ``valid``.
    stride : int, optional
        Stride used in the convolution operation. Defaults to ``1``.
    dilation : int, optional
        Dilation factor to use for each axis of the filter. Defaults to ``1``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.Convolution2d`
    """
    return FConvolution2D.forward(PseudoCache(), x, f, b, padding, stride, dilation)


class FDilation2D(Function):
    """Dilates a tensor in its last two axes."""

    @staticmethod
    def forward(cache: FunctionCache, x: Tensor, dilation: tuple[int, int]) -> Tensor:
        cache.no_dilation = dilation == (1, 1)
        if dilation == (1, 1):
            return x

        dil_shape = (
            dilation[0] * x.shape[-2] - 1,
            dilation[1] * x.shape[-1] - 1,
        )
        y = zeros(x.shape[:-2] + dil_shape, x.device, x.dtype)
        y[..., :: dilation[0], :: dilation[1]] = x

        cache.dilation = dilation
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        no_dilation, dilation = cache.no_dilation, cache.dilation
        if no_dilation:
            return dy
        return dy[..., :: dilation[0], :: dilation[1]]


def dilate2d(x: Tensor, dilation: tuple[int, int]) -> Tensor:
    """Dilates a tensor in its last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    dilation : tuple[int, int]
        Dilation factor to use.

    Returns
    -------
    Tensor
        Output tensor.
    """
    return FDilation2D.forward(PseudoCache(), x, dilation)


class FPad2D(Function):
    """Pads a tensor in its last two axes."""

    @staticmethod
    def forward(
        cache: FunctionCache,
        x: Tensor,
        padding: tuple[tuple[int, int], tuple[int, int]],
    ) -> Tensor:
        cache.no_padding = padding == ((0, 0), (0, 0))
        if padding == ((0, 0), (0, 0)):
            return x
        widths = tuple([(0, 0)] * (x.n_axes - 2) + [*padding])
        y = pad(x, widths)
        cache.padding = padding
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        no_padding, padding = cache.no_padding, cache.padding
        if no_padding:
            return dy
        return dy[..., padding[0][0] : -padding[0][1], padding[1][0] : -padding[1][1]]


def pad2d(x: Tensor, padding: tuple[tuple[int, int], tuple[int, int]]) -> Tensor:
    """Pads a tensor in its last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    padding : tuple[tuple[int, int], tuple[int, int]]
        Padding width applied to the beginning and end of the last two axes.

    Returns
    -------
    Tensor
        Output tensor.
    """
    return FPad2D.forward(PseudoCache(), x, padding)


def _pad2d_from_str(
    padding: PaddingLike, kernel_size: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    if padding == "valid":
        return ((0, 0), (0, 0))
    p = kernel_size // 2
    return ((p, p), (p, p))


class _FConvolution2D(Function):
    """Computes the 2D convolution of two tensors."""

    @staticmethod
    def forward(
        cache: FunctionCache, x: Tensor, f: Tensor, strides: tuple[int, int]
    ) -> Tensor:
        f_flipped = flip(f, (-2, -1))
        conv = convolve2d_fft(x, f_flipped)
        y = conv[..., :: strides[0], :: strides[1]]

        cache.x, cache.f, cache.strides, cache.conv_shape = x, f, strides, conv.shape
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> tuple[Tensor, Tensor]:
        x, f, strides, conv_shape = cache.x, cache.f, cache.strides, cache.conv_shape

        # fill elements skipped by strides with zeros
        dy = dilate2d(dy, strides)
        dy = pad_to_shape(dy, conv_shape)

        # full pad dy
        dy = pad2d(
            dy,
            (
                (f.shape[-2] - 1, f.shape[-2] - 1),
                (f.shape[-1] - 1, f.shape[-1] - 1),
            ),
        )
        dx = convolve2d_fft(dy, f)

        dy = flip(dy, (-2, -1))
        df = convolve2d_fft(dy, x)

        return dx, df


class FUpsample2D(Function):
    """Upsamples a tensor by repeating it's elements over the last two axes."""

    @staticmethod
    def forward(
        x: Tensor, scaling_factors: tuple[int, int], shape: ShapeLike
    ) -> Tensor:
        f1, f2 = scaling_factors
        x = repeat(repeat(x, f1, -1), f2, -2)
        y = x if x.shape == shape else pad_to_shape(x, shape)
        return y


def upsample2d(x: Tensor, scaling_factors: tuple[int, int], shape: ShapeLike) -> Tensor:
    """Upsamples a tensor by repeating it's elements over the last two axes.

    Parameters
    ----------
    x : Tensor
        Tensor to be stretched out.
    scaling_factors : tuple[int, int]
        Number of repeating values along each axis.
    shape : ShapeLike
        Shape of the target tensor. If the shape does not match after upsampling,
        remaining values are filled with zeroes.

    Returns
    -------
    Tensor
        Upsampled tensor.
    """
    return FUpsample2D.forward(x, scaling_factors, shape)


class FMaxPooling2D(Function):
    """Performs max pooling over the last two axes."""

    @staticmethod
    def forward(
        cache: FunctionCache, x: Tensor, kernel_size: tuple[int, int]
    ) -> Tensor:
        x_height, x_width = x.shape[-2:]
        kernel_height, kernel_width = kernel_size

        trunc_y = x_height // kernel_height * kernel_height
        trunc_x = x_width // kernel_width * kernel_width
        x_trunc = x[..., :trunc_y, :trunc_x]
        pool_shape = x.shape[:-2] + (
            x_height // kernel_height,
            kernel_height,
            x_width // kernel_width,
            kernel_width,
        )
        y = cp_max(x_trunc.to_shape(pool_shape), axis=(-3, -1))

        cache.x, cache.kernel_size, cache.y = x, kernel_size, y
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        x, kernel_size, y = cache.x, cache.kernel_size, cache.y
        y_ups = upsample2d(y, kernel_size, x.shape)
        return upsample2d(dy, kernel_size, x.shape) * (x == y_ups)


def maxpooling2d(x: Tensor, kernel_size: tuple[int, int] = (2, 2)) -> Tensor:
    """Performs max pooling over the last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    kernel_size : tuple[int, int], optional
        Size of the pooling window. Defaults to ``(2, 2)``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.MaxPooling2D`
    """
    return FMaxPooling2D.forward(PseudoCache(), x, kernel_size)


class FAvgPooling2D(Function):
    """Performs average pooling over the last two axes."""

    @staticmethod
    def forward(
        cache: FunctionCache, x: Tensor, kernel_size: tuple[int, int]
    ) -> Tensor:
        x_height, x_width = x.shape[-2:]
        kernel_height, kernel_width = kernel_size

        trunc_y = x_height // kernel_height * kernel_height
        trunc_x = x_width // kernel_width * kernel_width
        x_trunc = x[..., :trunc_y, :trunc_x]

        pool_shape = x.shape[:-2] + (
            x_height // kernel_height,
            kernel_height,
            x_width // kernel_width,
            kernel_width,
        )
        y = mean(x_trunc.to_shape(pool_shape), axis=(-3, -1))

        cache.x_shape, cache.kernel_size = x.shape, kernel_size
        return y

    @staticmethod
    def backward(cache: FunctionCache, dy: Tensor) -> Tensor:
        x_shape, kernel_size = cache.x_shape, cache.kernel_size
        return upsample2d(dy, kernel_size, x_shape) / math.prod(kernel_size)


def avgpooling2d(x: Tensor, kernel_size: tuple[int, int] = (2, 2)) -> Tensor:
    """Performs average pooling over the last two axes.

    Parameters
    ----------
    x : Tensor
        Input tensor.
    kernel_size : tuple[int, int], optional
        Size of the pooling window. Defaults to ``(2, 2)``.

    Returns
    -------
    Tensor
        Output tensor.

    See Also
    ----------
    :class:`compyute.nn.AvgPooling2D`
    """
    return FAvgPooling2D.forward(PseudoCache(), x, kernel_size)
