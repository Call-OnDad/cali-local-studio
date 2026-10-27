"""Container compatibility: explicit ONNX CPU threads and disabled telemetry.

Loaded only in our two server services via PYTHONPATH. Upstream packages remain
unmodified. Explicit threads prevent ORT's physical-core affinity assumptions
from targeting CPUs outside this LXC's cpuset.
"""
try:
    import onnxruntime as ort
    ort.disable_telemetry_events()
    OriginalSession=ort.InferenceSession
    class LocalSession(OriginalSession):
        def __init__(self,path_or_bytes,sess_options=None,*args,**kwargs):
            if sess_options is None:sess_options=ort.SessionOptions()
            if sess_options.intra_op_num_threads==0:sess_options.intra_op_num_threads=2
            if sess_options.inter_op_num_threads==0:sess_options.inter_op_num_threads=1
            super().__init__(path_or_bytes,sess_options,*args,**kwargs)
    ort.InferenceSession=LocalSession
except ImportError:
    pass
