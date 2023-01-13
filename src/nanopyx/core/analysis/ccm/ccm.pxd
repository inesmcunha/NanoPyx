cdef float[:, :, :] _calculate_ccm(float[:, :, :] img_stack, int ref)
cdef float[:, :, :] _calculate_ccm_from_ref(float[:, :, :] img_stack, float[:, :] img_ref)
cdef float[:, :] _calculate_slice_ccm(float[:, :] img_ref, float[:, :] img_slice)
cdef void _normalize_ccm(float[:, :] img_ref, float[:, :] img_slice, float[:, :] ccm_slice) nogil