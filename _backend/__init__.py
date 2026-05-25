from .interface import BackendInterface, BackendSignals


def get_backend(use_cpp: bool, project_root, parent=None) -> BackendInterface:
    if use_cpp:
        from .cpp.bridge import CppSharedMemBackend
        return CppSharedMemBackend(project_root=project_root, parent=parent)
    from .python.xcp_worker import PythonXcpBackend
    return PythonXcpBackend(project_root=project_root, parent=parent)
