# cython: infer_types=True, wraparound=False, nonecheck=False, boundscheck=False, cdivision=True, language_level=3, profile=False, autogen_pxd=False

import numpy as np
cimport numpy as np

from cython.parallel import parallel, prange

from libc.math cimport sqrt, pi, fabs, cos, sin
from .__liquid_engine__ import LiquidEngine
from .__interpolation_tools__ import check_image
from nanopyx.liquid import CRShiftAndMagnify
from nanopyx.core.utils.timeit import timeit2

cdef extern from "_c_interpolation_catmull_rom.h":
    pass

cdef extern from "_c_sr_radiality.h":
    float _c_calculate_radiality_per_subpixel(int i, int j, float* imGx, float* imGy, float* xRingCoordinates, float* yRingCoordinates, int magnification, float ringRadius, int nRingCoordinates, int radialityPositivityConstraint, int h, int w) nogil

cdef extern from "_c_gradients.h":
    void _c_gradient_radiality(float* image, float* imGc, float* imGr, int rows,
                          int cols) nogil

# cdef float Gx_Gy_MAGNIFICATION = 2.0

class Radiality(LiquidEngine):
    """
    Radial gradient convergence using the NanoPyx Liquid Engine
    """

    _has_opencl = False
    _has_threaded = True
    _has_threaded_static = True
    _has_threaded_dynamic = True
    _has_threaded_guided = True
    _has_unthreaded = True
    _has_python = False
    _has_njit = False

    def __init__(self):
        super().__init__()
    
    @timeit2
    def run(self, image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True, run_type = None): 
        image = check_image(image)
        return self._run(image, magnification, ringRadius, border, radialityPositivityConstraint, doIntensityWeighting, run_type=run_type)
    
    def benchmark(self, image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True): 
        image = check_image(image)
        return super().benchmark(image, magnification, ringRadius, border, radialityPositivityConstraint, doIntensityWeighting)
    
     # tag-start: _le_radiality.Radiality._run_unthreaded
    def _run_unthreaded(self, float[:,:,:] image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True):

        cdef int _magnification = magnification
        cdef int _border = border
        cdef float _ringRadius = ringRadius * magnification
        cdef int _doIntensityWeighting = doIntensityWeighting
        cdef int _radialityPositivityConstraint = radialityPositivityConstraint
        cdef int nRingCoordinates = 12
        cdef float angleStep = (pi * 2.) / nRingCoordinates
        cdef float[12] xRingCoordinates, yRingCoordinates

        with nogil:
            for angleIter in range(nRingCoordinates):
                xRingCoordinates[angleIter] = cos(angleStep * angleIter) * _ringRadius
                yRingCoordinates[angleIter] = sin(angleStep * angleIter) * _ringRadius
        
        cdef int nFrames = image.shape[0]
        cdef int h = image.shape[1]
        cdef int w = image.shape[2]

        crsm = CRShiftAndMagnify()
        cdef float [:,:,:] image_interp = crsm.run(image, 0, 0, magnification, magnification)
        
        cdef float [:,:,:] imGx = np.zeros_like(image) 
        cdef float [:,:,:] imGy = np.zeros_like(image)
        cdef float [:,:,:] imRad = np.zeros((nFrames, h*magnification, w*magnification), dtype=np.float32)

        cdef int f, j, i
        with nogil:
            for f in range(nFrames):
                 _c_gradient_radiality(&image[f,0,0], &imGx[f,0,0], &imGy[f,0,0], h, w)
                 for j in range((1 + _border) * _magnification, (h - 1 - _border) * _magnification):
                    for i in range((1 + _border) * _magnification, (w - 1 - _border) * _magnification):
                        if _doIntensityWeighting:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w) * image_interp[f, j, i]
                        else:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w)

        return imRad
        # tag-end

    # tag-copy:  _le_radiality.Radiality._run_unthreaded; replace("_run_unthreaded", "_run_threaded"); replace("range((1 + _border) * _magnification, (h - 1 - _border) * _magnification)", "prange((1 + _border) * _magnification, (h - 1 - _border) * _magnification)")
    def _run_threaded(self, float[:,:,:] image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True):

        cdef int _magnification = magnification
        cdef int _border = border
        cdef float _ringRadius = ringRadius * magnification
        cdef int _doIntensityWeighting = doIntensityWeighting
        cdef int _radialityPositivityConstraint = radialityPositivityConstraint
        cdef int nRingCoordinates = 12
        cdef float angleStep = (pi * 2.) / nRingCoordinates
        cdef float[12] xRingCoordinates, yRingCoordinates

        with nogil:
            for angleIter in range(nRingCoordinates):
                xRingCoordinates[angleIter] = cos(angleStep * angleIter) * _ringRadius
                yRingCoordinates[angleIter] = sin(angleStep * angleIter) * _ringRadius
        
        cdef int nFrames = image.shape[0]
        cdef int h = image.shape[1]
        cdef int w = image.shape[2]

        crsm = CRShiftAndMagnify()
        cdef float [:,:,:] image_interp = crsm.run(image, 0, 0, magnification, magnification)
        
        cdef float [:,:,:] imGx = np.zeros_like(image) 
        cdef float [:,:,:] imGy = np.zeros_like(image)
        cdef float [:,:,:] imRad = np.zeros((nFrames, h*magnification, w*magnification), dtype=np.float32)

        cdef int f, j, i
        with nogil:
            for f in range(nFrames):
                 _c_gradient_radiality(&image[f,0,0], &imGx[f,0,0], &imGy[f,0,0], h, w)
                 for j in prange((1 + _border) * _magnification, (h - 1 - _border) * _magnification):
                    for i in range((1 + _border) * _magnification, (w - 1 - _border) * _magnification):
                        if _doIntensityWeighting:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w) * image_interp[f, j, i]
                        else:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w)

        return imRad
        # tag-end


        #TODO: fix tag2tag, it couldnt replace by a prange(start,end,schedule)
    def _run_threaded_static(self, float[:,:,:] image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True):

        cdef int _magnification = magnification
        cdef int _border = border
        cdef float _ringRadius = ringRadius * magnification
        cdef int _doIntensityWeighting = doIntensityWeighting
        cdef int _radialityPositivityConstraint = radialityPositivityConstraint
        cdef int nRingCoordinates = 12
        cdef float angleStep = (pi * 2.) / nRingCoordinates
        cdef float[12] xRingCoordinates, yRingCoordinates

        with nogil:
            for angleIter in range(nRingCoordinates):
                xRingCoordinates[angleIter] = cos(angleStep * angleIter) * _ringRadius
                yRingCoordinates[angleIter] = sin(angleStep * angleIter) * _ringRadius
        
        cdef int nFrames = image.shape[0]
        cdef int h = image.shape[1]
        cdef int w = image.shape[2]

        crsm = CRShiftAndMagnify()
        cdef float [:,:,:] image_interp = crsm.run(image, 0, 0, magnification, magnification)
        
        cdef float [:,:,:] imGx = np.zeros_like(image) 
        cdef float [:,:,:] imGy = np.zeros_like(image)
        cdef float [:,:,:] imRad = np.zeros((nFrames, h*magnification, w*magnification), dtype=np.float32)

        cdef int f, j, i
        with nogil:
            for f in range(nFrames):
                _c_gradient_radiality(&image[f,0,0], &imGx[f,0,0], &imGy[f,0,0], h, w)
                for j in prange((1 + _border) * _magnification, (h - 1 - _border) * _magnification, schedule = "static"):
                    for i in range((1 + _border) * _magnification, (w - 1 - _border) * _magnification):
                        if _doIntensityWeighting:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w) * image_interp[f, j, i]
                        else:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w)

        return imRad

    def _run_threaded_dynamic(self, float[:,:,:] image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True):

        cdef int _magnification = magnification
        cdef int _border = border
        cdef float _ringRadius = ringRadius * magnification
        cdef int _doIntensityWeighting = doIntensityWeighting
        cdef int _radialityPositivityConstraint = radialityPositivityConstraint
        cdef int nRingCoordinates = 12
        cdef float angleStep = (pi * 2.) / nRingCoordinates
        cdef float[12] xRingCoordinates, yRingCoordinates

        with nogil:
            for angleIter in range(nRingCoordinates):
                xRingCoordinates[angleIter] = cos(angleStep * angleIter) * _ringRadius
                yRingCoordinates[angleIter] = sin(angleStep * angleIter) * _ringRadius
        
        cdef int nFrames = image.shape[0]
        cdef int h = image.shape[1]
        cdef int w = image.shape[2]

        crsm = CRShiftAndMagnify()
        cdef float [:,:,:] image_interp = crsm.run(image, 0, 0, magnification, magnification)
        
        cdef float [:,:,:] imGx = np.zeros_like(image) 
        cdef float [:,:,:] imGy = np.zeros_like(image)
        cdef float [:,:,:] imRad = np.zeros((nFrames, h*magnification, w*magnification), dtype=np.float32)

        cdef int f, j, i
        with nogil:
            for f in range(nFrames):
                 _c_gradient_radiality(&image[f,0,0], &imGx[f,0,0], &imGy[f,0,0], h, w)
                 for j in prange((1 + _border) * _magnification, (h - 1 - _border) * _magnification, schedule = "dynamic"):
                    for i in range((1 + _border) * _magnification, (w - 1 - _border) * _magnification):
                        if _doIntensityWeighting:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w) * image_interp[f, j, i]
                        else:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w)

        return imRad

    def _run_threaded_guided(self, float[:,:,:] image, magnification: int = 5, ringRadius: float = 0.5, border: int = 0, radialityPositivityConstraint: bool = True, doIntensityWeighting: bool = True):

        cdef int _magnification = magnification
        cdef int _border = border
        cdef float _ringRadius = ringRadius * magnification
        cdef int _doIntensityWeighting = doIntensityWeighting
        cdef int _radialityPositivityConstraint = radialityPositivityConstraint
        cdef int nRingCoordinates = 12
        cdef float angleStep = (pi * 2.) / nRingCoordinates
        cdef float[12] xRingCoordinates, yRingCoordinates

        with nogil:
            for angleIter in range(nRingCoordinates):
                xRingCoordinates[angleIter] = cos(angleStep * angleIter) * _ringRadius
                yRingCoordinates[angleIter] = sin(angleStep * angleIter) * _ringRadius
        
        cdef int nFrames = image.shape[0]
        cdef int h = image.shape[1]
        cdef int w = image.shape[2]

        crsm = CRShiftAndMagnify()
        cdef float [:,:,:] image_interp = crsm.run(image, 0, 0, magnification, magnification)
        
        cdef float [:,:,:] imGx = np.zeros_like(image) 
        cdef float [:,:,:] imGy = np.zeros_like(image)
        cdef float [:,:,:] imRad = np.zeros((nFrames, h*magnification, w*magnification), dtype=np.float32)

        cdef int f, j, i
        with nogil:
            for f in range(nFrames):
                 _c_gradient_radiality(&image[f,0,0], &imGx[f,0,0], &imGy[f,0,0], h, w)
                 for j in prange((1 + _border) * _magnification, (h - 1 - _border) * _magnification, schedule = "guided"):
                    for i in range((1 + _border) * _magnification, (w - 1 - _border) * _magnification):
                        if _doIntensityWeighting:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w) * image_interp[f, j, i]
                        else:
                            imRad[f,j,i] = _c_calculate_radiality_per_subpixel(i, j, &imGx[f,0,0], &imGy[f,0,0], xRingCoordinates, yRingCoordinates, _magnification, _ringRadius, nRingCoordinates, _radialityPositivityConstraint, h, w)

        return imRad