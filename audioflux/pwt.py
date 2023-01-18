import warnings

import numpy as np
from ctypes import Structure, POINTER, pointer, c_int, c_float, c_void_p
from audioflux.type import SpectralFilterBankScaleType, SpectralFilterBankStyleType, SpectralFilterBankNormalType
from audioflux.base import Base
from audioflux.utils import check_audio, check_audio_length, note_to_hz

__all__ = ["PWT"]


class OpaquePWT(Structure):
    _fields_ = []


class PWT(Base):
    """
    Pseudo Wavelet Transform (PWT).

    Parameters
    ----------
    num: int
        Number of frequency bins to generate, starting at `low_fre`.

    radix2_exp: int
        ``fft_length=2**radix2_exp``

    samplate: int
        Sampling rate of the incoming audio.

    low_fre: float or None
        Lowest frequency.

        - Linear/Linsapce/Mel/Bark/Erb, low_fre>=0. `default: 0.0`
        - Octave/Log, low_fre>=32.703. `default: 32.703(C1)`

    high_fre: float or None
        Highest frequency. Default is `16000(samplate/2)`.

        - Linear is not provided, it is based on ``samplate / (2 ** radix2_exp)``.
        - Octave is not provided, it is based on musical pitch.

    bin_per_octave: int
        Number of bins per octave.

        Only Octave must be provided.

    scale_type: SpectralFilterBankScaleType
        Spectral filter bank type. It determines the type of spectrogram.

        See: `type.SpectralFilterBankScaleType`

    style_type: SpectralFilterBankStyleType
        Spectral filter bank style type. It determines the bank type of window.

        see: `type.SpectralFilterBankStyleType`

    normal_type: SpectralFilterBankNormalType
        Spectral filter normal type. It determines the type of normalization.

        Linear is not provided.

        See: `type.SpectralFilterBankNormalType`

    is_padding: bool
        Whether to use padding.

    See Also
    --------
    BFT
    NSGT
    CWT

    Examples
    --------

    Read 220Hz audio data

    >>> import audioflux as af
    >>> audio_path = af.utils.sample_path('220')
    >>> audio_arr, sr = af.read(audio_path)
    >>> # PWT can only input fft_length data
    >>> # For radix2_exp=12, then fft_length=4096
    >>> audio_arr = audio_arr[:4096]
    array([-5.5879354e-09, -9.3132257e-09,  0.0000000e+00, ...,
           -1.3137090e-01, -1.5649168e-01, -1.8550715e-01], dtype=float32)

    Create PWT object of Octave

    >>> from audioflux.type import (SpectralFilterBankScaleType, SpectralFilterBankStyleType,
    >>>                             SpectralFilterBankNormalType)
    >>> from audioflux.utils import note_to_hz
    >>> obj = af.PWT(num=84, radix2_exp=12, samplate=sr,
    >>>               low_fre=note_to_hz('C1'), bin_per_octave=12,
    >>>               scale_type=SpectralFilterBankScaleType.OCTAVE,
    >>>               style_type=SpectralFilterBankStyleType.SLANEY,
    >>>               normal_type=SpectralFilterBankNormalType.NONE)

    Extract spectrogram

    >>> import numpy as np
    >>> spec_arr = obj.pwt(audio_arr)
    >>> spec_arr = np.abs(spec_arr)
    array([[2.0927351e-04, 2.0927349e-04, 2.0927351e-04, ..., 2.0927351e-04,
            2.0927349e-04, 2.0927351e-04],
           [3.3626966e-03, 3.3626966e-03, 3.3626969e-03, ..., 3.3626969e-03,
            3.3626969e-03, 3.3626966e-03],
           [1.1016995e-03, 1.1016995e-03, 1.1016997e-03, ..., 1.1016995e-03,
            1.1016997e-03, 1.1016995e-03],
           ...,
           [4.2387177e-04, 4.2435329e-04, 4.2531796e-04, ..., 1.5332833e-03,
            1.5327019e-03, 1.5324111e-03],
           [1.4914650e-05, 1.4527454e-05, 1.3769239e-05, ..., 3.9103269e-04,
            3.9109713e-04, 3.9112900e-04],
           [2.5504729e-04, 2.5552284e-04, 2.5647049e-04, ..., 3.5153513e-04,
            3.5086548e-04, 3.5052933e-04]], dtype=float32)

    Show spectrogram plot

    >>> import matplotlib.pyplot as plt
    >>> from audioflux.display import fill_spec
    >>> fig, ax = plt.subplots()
    >>> img = fill_spec(spec_arr, axes=ax,
    >>>                 x_coords=obj.x_coords(),
    >>>                 y_coords=obj.y_coords(),
    >>>                 x_axis='time', y_axis='log',
    >>>                 title='PWT-Octave Spectrogram')
    >>> fig.colorbar(img, ax=ax)
    """

    def __init__(self, num, radix2_exp=12, samplate=32000,
                 low_fre=0., high_fre=16000., bin_per_octave=12,
                 scale_type=SpectralFilterBankScaleType.OCTAVE,
                 style_type=SpectralFilterBankStyleType.SLANEY,
                 normal_type=SpectralFilterBankNormalType.NONE,
                 is_padding=True):
        super(PWT, self).__init__(pointer(OpaquePWT()))

        # check BPO
        if scale_type == SpectralFilterBankScaleType.OCTAVE and bin_per_octave < 1:
            raise ValueError(f'bin_per_octave={bin_per_octave} must be a positive integer')

        if low_fre is None:
            if scale_type in (SpectralFilterBankScaleType.OCTAVE,
                              SpectralFilterBankScaleType.LOG):
                low_fre = note_to_hz('C1')  # 32.703
            else:
                low_fre = 0.0

        if high_fre is None:
            high_fre = samplate / 2

        # check low_fre
        if scale_type in (SpectralFilterBankScaleType.OCTAVE,
                          SpectralFilterBankScaleType.LOG) \
                and low_fre < round(note_to_hz('C1'), 3):
            # Octave/Log >= 32.703
            raise ValueError(f'{scale_type.name} low_fre={low_fre} must be greater than or equal to 32.703')
        if low_fre < 0:
            # linear/linspace/mel/bark/erb low_fre>=0
            raise ValueError(f'{scale_type.name} low_fre={low_fre} must be a non-negative number')

        self.num = num
        self.radix2_exp = radix2_exp
        self.samplate = samplate
        self.low_fre = low_fre
        self.high_fre = high_fre
        self.bin_per_octave = bin_per_octave
        self.scale_type = scale_type
        self.style_type = style_type
        self.normal_type = normal_type
        self.is_padding = is_padding

        self.fft_length = 1 << radix2_exp

        fn = self._lib['pwtObj_new']
        fn.argtypes = [POINTER(POINTER(OpaquePWT)), c_int, c_int,
                       POINTER(c_int), POINTER(c_float), POINTER(c_float), POINTER(c_int),
                       POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int)]
        fn(self._obj,
           c_int(self.num),
           c_int(self.radix2_exp),
           pointer(c_int(self.samplate)),
           pointer(c_float(self.low_fre)),
           pointer(c_float(self.high_fre)),
           pointer(c_int(self.bin_per_octave)),
           pointer(c_int(self.scale_type.value)),
           pointer(c_int(self.style_type.value)),
           pointer(c_int(self.normal_type.value)),
           pointer(c_int(int(self.is_padding))))
        self._is_created = True

    def get_fre_band_arr(self):
        """
        Get an array of frequency bands of different scales.
        Based on the `scale_type` determination of the initialization.

        Returns
        -------
        out: np.ndarray [shape=(fre, )]
        """

        fn = self._lib['pwtObj_getFreBandArr']
        fn.argtypes = [POINTER(OpaquePWT)]
        fn.restype = c_void_p
        p = fn(self._obj)
        ret = np.frombuffer((c_float * self.num).from_address(p), np.float32).copy()
        return ret

    def get_bin_band_arr(self):
        """
        Get bin band array

        Returns
        -------
        out: np.ndarray [shape=[n_bin,]]
        """

        fn = self._lib['pwtObj_getBinBandArr']
        fn.argtypes = [POINTER(OpaquePWT)]
        fn.restype = c_void_p
        p = fn(self._obj)
        ret = np.frombuffer((c_int * self.num).from_address(p), np.int32).copy()
        return ret

    def pwt(self, data_arr):
        """
        Get spectrogram data

        Parameters
        ----------
        data_arr: np.ndarray [shape=(n,)]
            Audio data array

        Returns
        -------
        out: np.ndarray [shape=(fre, time)]
            The matrix of PWT
        """

        data_arr = np.asarray(data_arr, dtype=np.float32, order='C')
        check_audio(data_arr)
        data_arr = check_audio_length(data_arr, self.radix2_exp)

        fn = self._lib['pwtObj_pwt']
        fn.argtypes = [POINTER(OpaquePWT),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                       ]

        real_arr = np.zeros((self.num, self.fft_length), dtype=np.float32)
        imag_arr = np.zeros((self.num, self.fft_length), dtype=np.float32)

        fn(self._obj, data_arr, real_arr, imag_arr)
        m_pwt_arr = real_arr + imag_arr * 1j
        return m_pwt_arr

    def enable_det(self, flag):
        """
        Enable det

        Parameters
        ----------
        flag: bool

        Returns
        -------

        """
        fn = self._lib['pwtObj_enableDet']
        fn.argtypes = [POINTER(OpaquePWT), c_int]
        fn(self._obj, c_int(int(flag)))

    def pwt_det(self, data_arr):
        """
        Get pwt det data

        Parameters
        ----------
        data_arr: np.ndarray [shape=(n,)]
            Audio data array

        Returns
        -------
        out: np.ndarray [shape=(fre, time)]
        """

        data_arr = np.asarray(data_arr, dtype=np.float32, order='C')
        check_audio(data_arr)
        data_arr = check_audio_length(data_arr, self.radix2_exp)

        fn = self._lib['pwtObj_pwtDet']
        fn.argtypes = [POINTER(OpaquePWT),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                       np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
                       ]

        real_arr = np.zeros((self.num, self.fft_length), dtype=np.float32)
        imag_arr = np.zeros((self.num, self.fft_length), dtype=np.float32)

        fn(self._obj, data_arr, real_arr, imag_arr)
        m_pwt_det_arr = real_arr + imag_arr * 1j
        return m_pwt_det_arr

    def y_coords(self):
        """
        Get the Y-axis coordinate

        Returns
        -------
        out: np.ndarray [shape=(fre,)]
        """
        y_coords = self.get_fre_band_arr()
        y_coords = np.insert(y_coords, 0, self.low_fre)
        return y_coords

    def x_coords(self):
        """
        Get the X-axis coordinate

        Returns
        -------
        out: np.ndarray [shape=(time,)]
        """
        x_coords = np.linspace(0, self.fft_length / self.samplate, self.fft_length + 1)
        return x_coords

    def __del__(self):
        if self._is_created:
            fn = self._lib['pwtObj_free']
            fn.argtypes = [POINTER(OpaquePWT)]
            fn.restype = c_void_p
            fn(self._obj)
