from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Sequence, Tuple, Union
import numpy as np
from cffi import FFI

ffi = FFI()

C_HEADER = """
typedef struct {
    float b0;
    float b1;
    float b2;
    float a1;
    float a2;
} synapse_biquad_coeffs_t;

typedef struct {
    float s1;
    float s2;
} synapse_biquad_state_t;

typedef struct {
    uint32_t num_channels;
    uint32_t num_sections;
    synapse_biquad_coeffs_t *coeffs;
    synapse_biquad_state_t  *states;
} synapse_biquad_cascade_t;

int synapse_biquad_cascade_init(synapse_biquad_cascade_t *cascade,
                                uint32_t num_channels,
                                uint32_t num_sections,
                                const synapse_biquad_coeffs_t *coeffs);

void synapse_biquad_cascade_free(synapse_biquad_cascade_t *cascade);
void synapse_biquad_cascade_reset(synapse_biquad_cascade_t *cascade);
bool synapse_biquad_verify_stability(const synapse_biquad_coeffs_t *coeffs);

void synapse_biquad_process_sample(synapse_biquad_cascade_t *cascade,
                                   const float *in_frame,
                                   float *out_frame);

void synapse_biquad_process_block(synapse_biquad_cascade_t *cascade,
                                  uint32_t channel_idx,
                                  const float *in_samples,
                                  float *out_samples,
                                  size_t num_samples);
"""

ffi.cdef(C_HEADER)

def _load_native_library():
    lib_name = "libsynapse_biquad.dylib" if platform.system() == "Darwin" else "libsynapse_biquad.so"
    if platform.system() == "Windows":
        lib_name = "synapse_biquad.dll"

    search_dirs = [
        Path(__file__).parent,
        Path(__file__).parent / "build",
        Path(__file__).parent.parent / "csrc",
        Path("/usr/local/lib"),
    ]

    for d in search_dirs:
        candidate = d / lib_name
        if candidate.exists():
            return ffi.dlopen(str(candidate.resolve()))

    try:
        return ffi.dlopen(lib_name)
    except OSError as err:
        raise RuntimeError(
            f"Unable to locate compiled native library '{lib_name}'. "
            f"Build it with clang before importing."
        ) from err

_lib = _load_native_library()

class NativeBiquadCascade:
    __slots__ = ("_cascade", "num_channels", "num_sections", "_is_initialized")

    def __init__(
        self,
        num_channels: int,
        coefficients: Sequence[Union[Sequence[float], Tuple[float, float, float, float, float]]],
    ):
        if num_channels <= 0:
            raise ValueError(f"num_channels must be > 0, received {num_channels}")

        coeffs_arr = np.asarray(coefficients, dtype=np.float32)
        if coeffs_arr.ndim != 2 or coeffs_arr.shape[1] != 5:
            raise ValueError(
                f"coefficients array must have shape (num_sections, 5), received {coeffs_arr.shape}"
            )

        self.num_channels = int(num_channels)
        self.num_sections = int(coeffs_arr.shape[0])
        self._cascade = ffi.new("synapse_biquad_cascade_t *")
        self._is_initialized = False

        c_coeffs = ffi.new("synapse_biquad_coeffs_t[]", self.num_sections)
        for s in range(self.num_sections):
            c_coeffs[s].b0 = float(coeffs_arr[s, 0])
            c_coeffs[s].b1 = float(coeffs_arr[s, 1])
            c_coeffs[s].b2 = float(coeffs_arr[s, 2])
            c_coeffs[s].a1 = float(coeffs_arr[s, 3])
            c_coeffs[s].a2 = float(coeffs_arr[s, 4])

        ret = _lib.synapse_biquad_cascade_init(
            self._cascade,
            self.num_channels,
            self.num_sections,
            c_coeffs,
        )

        if ret == -2:
            raise ValueError("Biquad filter coefficients violate BIBO stability bounds (|p| >= 1.0).")
        elif ret != 0:
            raise RuntimeError(f"Native cascade initialization failed with code {ret}.")

        self._is_initialized = True

    def process_sample(
        self,
        in_frame: np.ndarray,
        out_frame: np.ndarray | None = None,
    ) -> np.ndarray:
        if in_frame.dtype != np.float32 or not in_frame.flags.c_contiguous:
            in_frame = np.ascontiguousarray(in_frame, dtype=np.float32)

        if in_frame.shape != (self.num_channels,):
            raise ValueError(
                f"Input frame shape {in_frame.shape} must match (num_channels={self.num_channels},)"
            )

        if out_frame is None:
            out_frame = np.empty_like(in_frame)
        else:
            if out_frame.dtype != np.float32 or not out_frame.flags.c_contiguous:
                raise ValueError("out_frame must be float32 and C-contiguous")
            if out_frame.shape != (self.num_channels,):
                raise ValueError(f"out_frame shape {out_frame.shape} mismatch with channels")

        c_in = ffi.cast("const float *", ffi.from_buffer(in_frame))
        c_out = ffi.cast("float *", ffi.from_buffer(out_frame))

        _lib.synapse_biquad_process_sample(self._cascade, c_in, c_out)
        return out_frame

    def process_block(
        self,
        channel_idx: int,
        in_samples: np.ndarray,
        out_samples: np.ndarray | None = None,
    ) -> np.ndarray:
        if channel_idx < 0 or channel_idx >= self.num_channels:
            raise IndexError(f"channel_idx {channel_idx} out of range [0, {self.num_channels})")

        if in_samples.dtype != np.float32 or not in_samples.flags.c_contiguous:
            in_samples = np.ascontiguousarray(in_samples, dtype=np.float32)

        n_samples = in_samples.size
        if out_samples is None:
            out_samples = np.empty_like(in_samples)
        else:
            if out_samples.dtype != np.float32 or not out_samples.flags.c_contiguous:
                raise ValueError("out_samples must be float32 and C-contiguous")
            if out_samples.size != n_samples:
                raise ValueError("out_samples size must match in_samples")

        c_in = ffi.cast("const float *", ffi.from_buffer(in_samples))
        c_out = ffi.cast("float *", ffi.from_buffer(out_samples))

        _lib.synapse_biquad_process_block(
            self._cascade,
            int(channel_idx),
            c_in,
            c_out,
            int(n_samples),
        )
        return out_samples

    def reset(self) -> None:
        if self._is_initialized:
            _lib.synapse_biquad_cascade_reset(self._cascade)

    def __del__(self) -> None:
        if getattr(self, "_is_initialized", False):
            _lib.synapse_biquad_cascade_free(self._cascade)
            self._is_initialized = False

def check_biquad_stability(b0: float, b1: float, b2: float, a1: float, a2: float) -> bool:
    c_coeff = ffi.new(
        "synapse_biquad_coeffs_t *",
        {"b0": b0, "b1": b1, "b2": b2, "a1": a1, "a2": a2},
    )
    return bool(_lib.synapse_biquad_verify_stability(c_coeff))
