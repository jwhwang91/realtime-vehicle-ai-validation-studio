# Mock Architecture Summary

```text
Mock ECU Signal Source
        │ synthetic DAQ samples
        ▼
C++ Mock xcp_backend / Python Mock Worker
        │ shared-memory-shaped snapshot API
        ▼
PyQt5 Frontend Controller
        │ ordered input dictionary
        ▼
Mock Model Block: demo_model.calculate(inputs)
        │ output characteristics
        ▼
Mock STIM Writer / Live Monitor
```

The structure follows a production-style E2E GUI layout, but all data and transport layers are synthetic.  
The goal is to demonstrate UI architecture, backend abstraction, mock IPC layout, C++ source organization, and safe portfolio presentation.
