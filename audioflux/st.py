import warnings

import numpy as np
from ctypes import Structure, POINTER, pointer, c_int, c_float, c_void_p
from audioflux.base import Base
from audioflux.utils import check_audio, check_audio_length

__all__ = ['ST']


class OpaqueST(Structure):
    _fields_ = []


class ST(Base):
    """
    S-Transform (ST)

    Parameters
    ----------
    radix2_exp: int
        ``fft_length=2**radix2_exp``

    min_index: int
        Min bank index.

        Available range: [1, max_index)

    max_index: int
        Max bank index.

        Available range: (min_index, fft_length/2)

    samplate: int
        Sampling rate of the incoming audio

    factor: float
        Factor value

    norm: float
        Norm value

    See Also
    --------
    CQT
    FST
    DWT
    WPT
    SWT

    Examples
    --------

    Read 880Hz audio data

    >>> import audioflux as af
    >>> audio_path = af.utils.sample_path('880')
    >>> audio_arr, sr = af.read(audio_path)
    >>> # ST can only input fft_length data
    >>> # For radix2_exp=12, then fft_length=4096
    >>> audio_arr = audio_arr[:4096]
    array([-5.5879354e-09, -9.3132257e-09,  0.0000000e+00, ...,
           -1.3013066e-01, -8.8289484e-02, -7.2360471e-02], dtype=float32)

    Create ST object

    >>> min_index, max_index = 1, 1024    # frequency is about 7.8125~8000Hz
    >>> obj = af.ST(radix2_exp=12, samplate=sr, min_index=min_index, max_index=max_index)

    Extract spectrogram

    >>> import numpy as np
    >>> spec_arr = obj.st(audio_arr)
    >>> spec_arr = np.abs(spec_arr)
    >>> spec_arr
    array([[0.00209793, 0.00209793, 0.00209793, ..., 0.00209793, 0.00209793,
            0.00209793],
           [0.00145852, 0.00145853, 0.00145855, ..., 0.00145848, 0.00145849,
            0.00145851],
           [0.00158793, 0.00158835, 0.00158878, ..., 0.00158667, 0.00158709,
            0.00158751],
           ...,
           [0.00688319, 0.00595584, 0.00489485, ..., 0.00790979, 0.00791093,
            0.00756201],
           [0.00688484, 0.0059536 , 0.00489008, ..., 0.00792713, 0.00792307,
            0.00756865],
           [0.00688638, 0.00595126, 0.00488525, ..., 0.00794437, 0.0079351 ,
            0.00757518]], dtype=float32)

    Show spectrogram plot

    >>> import matplotlib.pyplot as plt
    >>> from audioflux.display import fill_spec
    >>> fig, ax = plt.subplots()
    >>> img = fill_spec(spec_arr, axes=ax,
    >>>                 x_coords=obj.x_coords(),
    >>>                 y_coords=obj.y_coords(),
    >>>                 x_axis='time', y_axis='log',
    >>>                 title='ST Spectrogram')
    >>> fig.colorbar(img, ax=ax)
    """

    def __init__(self, radix2_exp=12, min_index=1, max_index=None, samplate=32000, factor=1., norm=1.):
        super(ST, self).__init__(pointer(OpaqueST()))

        fft_length = 1 << radix2_exp

        if max_index is None:
            max_index = (fft_length // 2) - 1

        if min_index < 1:
            raise ValueError(f'min_index={min_index} must be a positive integer.')
        if max_index >= (fft_length / 2):
            raise ValueError(f'max_index={max_index} must be less than or equal to fft_length/2={fft_length / 2}')
        if min_index >= max_index:
            raise ValueError(f'min_index={min_index} must be less than max_index={max_index}')

        self.radix2_exp = radix2_exp
        self.samplate = samplate
        self.min_index = min_index
        self.max_index = max_index
        self.factor = factor
        self.norm = norm

        self.fft_length = fft_length
        self.num = self.max_index - self.min_index + 1

        fn = self._lib['stObj_new']
        fn.argtypes = [POINTER(POINTER(OpaqueST)), c_int, c_int, c_int,
                       POINTER(c_float), POINTER(c_float)]
        fn(self._obj,
           c_int(self.radix2_exp),
           c_int(self.min_index),
           c_int(self.max_index),
           pointer(c_float(self.factor)),
           pointer(c_float(self.norm)))
        self._is_created = True

    def use_bin_arr(self, bin_arr):
        """
        Use bin arr

        Parameters
        ----------
        bin_arr: np.ndarray [shape=(n,)]
        """
        bin_arr = np.asarray(bin_arr, dtype=np.float32, order='C')
        if bin_arr.ndim != 1:
            raise ValueError('bin_arr is only defined for 1D arrays')

        length = bin_arr.shape[0]
        user_bin_arr_fn = self._lib['stObj_useBinArr']
        user_bin_arr_fn.argtypes = [POINTER(OpaqueST),
                                    np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
                                    c_int]
        user_bin_arr_fn(self._obj, bin_arr, c_int(length))

    def set_value(self, factor, norm):
        """
        Set value

        Parameters
        ----------
        factor: float
            Factor value

        norm: float
            Norm value
        """
        set_value_fn = self._lib['stObj_setValue']
        set_value_fn.argtypes = [POINTER(OpaqueST), c_float, c_float]
        set_value_fn(self._obj, c_float(factor), c_float(norm))

    def get_fre_band_arr(self):
        """
        Get an array of ST frequency bands of different scales.

        Returns
        -------
        out: np.ndarray [shape=(n_fre,)]
        """
        return np.arange(self.min_index, self.max_index + 1, dtype=np.float32) * self.samplate / self.fft_length

    def st(self, data_arr):
        """
        Get spectrogram data

        Parameters
        ----------
        data_arr: np.ndarray [shape=(n,)]
            Input audio data

        Returns
        -------
        out: np.ndarray [shape=(fre, time)]
        """
        data_arr = np.asarray(data_arr, dtype=np.float32, order='C')
        check_audio(data_arr)
        data_arr = check_audio_length(data_arr, self.radix2_exp)

        st_fn = self._lib['stObj_st']
        st_fn.argtypes = [POINTER(OpaqueST),
                          np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
                          np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                          np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                          ]

        size = (self.num, self.fft_length)
        m_real_arr = np.zeros(size, dtype=np.float32)
        m_imag_arr = np.zeros(size, dtype=np.float32)

        st_fn(self._obj, data_arr, m_real_arr, m_imag_arr)
        return m_real_arr + (m_imag_arr * 1j)

    def y_coords(self):
        """
        Get the Y-axis coordinate

        Returns
        -------
        out: np.ndarray
        """
        fre_band_arr = self.get_fre_band_arr()
        y_coords = np.insert(fre_band_arr, 0, fre_band_arr[0])
        return y_coords

    def x_coords(self):
        """
        Get the X-axis coordinate

        Returns
        -------
        out: np.ndarray
        """
        x_coords = np.linspace(0, self.fft_length / self.samplate, self.fft_length + 1)
        return x_coords

    def __del__(self):
        if self._is_created:
            free_fn = self._lib['stObj_free']
            free_fn.argtypes = [POINTER(OpaqueST)]
            free_fn.restype = c_void_p
            free_fn(self._obj)
