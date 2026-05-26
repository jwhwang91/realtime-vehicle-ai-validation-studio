# Real-Time Vehicle AI Validation Studio

> [!NOTE]
> This repository is a **public-safe portfolio mock**.  
> It does **not** contain proprietary company code, real ECU data, production A2L/ELF files, internal model assets, or confidential validation logic.  
> All signals, addresses, replay values, model files, Simulink paths, and backend data paths are synthetic.

A transport-adaptable **PyQt5 + C++ + MATLAB/Simulink vehicle AI validation studio mock** for real-time vehicle signal replay, AI model block validation, MBD-oriented signal interface preparation, and data-flow visualization.

This project demonstrates a public-facing version of a vehicle AI validation workflow originally designed under constrained hardware conditions. The available communication path was CAN-FD/XCP-style access, but the backend was intentionally separated behind a transport abstraction layer so that future Ethernet-based interfaces can be integrated without redesigning the UI, signal workflow, model validation canvas, or MBD preparation utilities.

---

## Repository Description

**Public-safe portfolio version of a transport-adaptable real-time vehicle AI validation studio using synthetic A2L, ELF, replay, model, and MATLAB/Simulink MBD utility data.**

---

## Demo

### Working Demo

![Working Demo](docs/media/demo.gif)

### Main Interface

![Main Interface](docs/media/screenshot_main.png)

Expected media structure:

```text
docs/
└── media/
    ├── demo.gif
    └── screenshot_main.png
```

If the images do not appear on GitHub, check that the actual file names and README paths match exactly.

---

## Why This Project Exists

Vehicle AI validation workflows often depend on specific hardware, ECU interfaces, calibration files, MATLAB/Simulink MBD workflows, auto-generated embedded C code, and internal toolchains.

In the original engineering context, the available hardware path was limited. If Ethernet measurement hardware had been available, the preferred validation path would have been Ethernet-based due to better throughput and scalability. However, under the available equipment constraints, the practical interface path was CAN-FD/XCP-style measurement and calibration access.

Because of that constraint, the system needed to extract the maximum value from the available communication path while keeping the software architecture expandable.

The key design decision was to separate the GUI and validation workflow from the transport backend:

```text
_backend/
├── mock backend
├── CAN-FD / XCP-style adapter concept
└── future Ethernet adapter extension point
```

This allows the same UI and model workflow to support different transport implementations later, including Ethernet-based measurement or calibration interfaces.

---

## MBD / Simulink Code Generation Context

The production-style development workflow behind this mock is based on MATLAB/Simulink Model-Based Design.

A typical embedded workflow is:

```text
Simulink model
→ auto code generation
→ generated C code
→ ECU flash
→ runtime measurement / calibration / validation
```

For AI validation, each module owner may need to temporarily convert a conventional module into an AI-learning or AI-validation module. In that case, the input signals required by the AI model must be exposed in a predictable embedded memory layout after code generation.

In a Simulink auto-code-generation workflow, this usually means:

1. Bringing the AI model input signals into a dedicated Simulink interface area.
2. Connecting those signals to a non-virtual bus.
3. Configuring the generated interface so the signals can be accessed as external/global data.
4. Ensuring the generated C struct layout is stable and efficient.
5. Mapping that generated layout to measurement/calibration metadata such as A2L/ELF-like symbol information.

This matters especially when the available runtime access path is constrained to CAN-FD/XCP-style measurement instead of a higher-throughput Ethernet path.

---

## Power of the MATLAB Bus Optimization Utility

The MATLAB utility is not just a documentation example. It demonstrates an MBD-side automation concept that would be valuable before the generated C code is flashed to the ECU.

```text
tools/matlab/buildOptimizedBusObjectFromModelBlock.m
```

The utility is designed to do four important things:

### 1. Automatically find non-virtual buses inside a Simulink model

Given a Simulink model block path, the script searches under that path and finds Bus Creator blocks that are likely used as non-virtual bus interfaces.

This matters because AI model input interfaces may be scattered across module-owned Simulink areas, and manual inspection is slow and error-prone.

### 2. Read the connected signal data types automatically

For each connected input signal, the script reads compiled signal metadata such as:

```text
signal name
source block
source port
compiled data type
dimensions
bus creator path
```

This prevents developers from manually ordering signals without considering generated C data types.

### 3. Create an optimized bus object in the MATLAB workspace

The script sorts signals from larger data types to smaller data types:

```text
double / uint64 / int64
single / uint32 / int32
uint16 / int16
boolean / uint8 / int8
```

Then it generates a `Simulink.Bus` object in the MATLAB base workspace.

The purpose is to make the generated C struct layout more stable and padding-aware. A manually ordered bus such as this:

```text
uint8
double
uint16
single
boolean
uint32
```

can be reorganized into a top-down order such as:

```text
double
uint32 / single
uint16
uint8 / boolean
```

This is especially useful when a validation tool needs predictable access to generated global/external data through measurement metadata.

### 4. Apply the optimized order back into the Simulink model

The key point is that the script does not stop at creating a bus object.

It can also reconnect the Bus Creator input lines in the optimized order so the Simulink model itself reflects the final bus ordering.

That means the optimized order can flow into the next auto code generation step:

```text
optimized Simulink bus connection order
→ optimized Simulink.Bus object
→ generated C struct field order
→ more predictable A2L/ELF-style runtime access
→ easier real-time validation under CAN-FD/XCP constraints
```

This fourth step is the main reason the script is useful. It reduces manual mistakes from module developers who may not consider data type size, padding, or signal order when wiring AI model inputs.

---

## MATLAB Utility Example

```matlab
[busObj, report] = buildOptimizedBusObjectFromModelBlock( ...
    "demo_model/AI_Input_Interface", ...
    "AI_Input_OptimizedBus", ...
    "ApplyToModel", true);
```

Optional arguments:

```matlab
"AssignToBase", true
"ApplyToModel", true
"CreateBackup", true
"Verbose", true
```

Expected conceptual output:

```text
AI_Input_OptimizedBus
├── signal_speed_double      double
├── signal_model_state_u32   uint32
├── signal_yaw_rate_single   single
├── signal_counter_u16       uint16
├── signal_flag_bool         boolean
└── signal_status_u8         uint8
```

This utility is included as a public-safe mock. It does not include real model paths, internal bus objects, production code generation settings, or real company signal names.

---

## Core Features

### Simulink-like Validation Canvas

- Drag/drop signals from the A2L signal list.
- Add model blocks.
- Move blocks freely.
- Select blocks individually.
- Ctrl-click to multi-select blocks.
- Rubber-band selection by dragging an area.
- Delete selected blocks with `Delete` or `Backspace`.
- Middle-mouse panning, similar to Simulink-style navigation.
- Click-to-connect port wiring.
- Cancel pending connection with `Esc` or right-click.

### Dynamic Model Blocks

Double-click a model block to open the configuration dialog:

- Select `.py` script or `.onnx` model file.
- Set input count.
- Set output count.
- The block graphically updates its input/output ports.
- Existing invalid connections are pruned when port count is reduced.

### Independent Port Connections

Each model input/output has its own graphical port. Each connection stores:

```text
source block
source port index
destination block
destination port index
data key
```

### Real-Time Data-Flow Visualization

During replay:

- Active connection lines turn white.
- Inactive connection lines remain green.
- Selected inactive lines are highlighted.
- Double-clicking a line opens a floating pyqtgraph window for real-time data-flow monitoring.

### Floating Graph Windows with pyqtgraph

The **ALL Graph** button opens floating real-time graphs for:

- DAQ / measurement signals
- model output values
- ECU write value
- jitter / replay timing metrics

### Mock A2L and ELF Integration

The project includes public-safe mock metadata:

- synthetic A2L signal definitions
- synthetic ELF symbol map
- synthetic signal addresses
- synthetic measurement and characteristic data

No real ECU calibration metadata is included.

### C++ Mock Backend

The repository includes a buildable C++ mock backend to demonstrate embedded/backend implementation capability. The C++ code is intentionally mock-only and does not communicate with real hardware.

---

## Tech Stack

| Area | Technology |
|---|---|
| MBD workflow | MATLAB / Simulink |
| Auto code generation concept | Simulink Coder / Embedded Coder-style workflow |
| Embedded interface concept | Generated C struct / external global data |
| MBD automation utility | MATLAB script for non-virtual bus detection, data-type sorting, and Simulink bus rewiring |
| GUI | PyQt5 |
| Real-time plotting | pyqtgraph |
| Backend mock | Python async worker |
| C++ backend mock | C++17 |
| Build system | CMake |
| Data files | Synthetic A2L, ELF, CSV-style replay |
| Architecture pattern | Transport-adaptable backend abstraction |
| Communication constraint represented | CAN-FD / XCP-style access |
| Future extension point | Ethernet transport adapter |
| Purpose | Public-safe portfolio demo |

---

## Project Structure

```text
realtime-vehicle-ai-validation-studio/
├── main.py
├── requirements.txt
├── README.md
├── _uiux/
├── _backend/
│   ├── mock_assets/
│   └── cpp/
├── _utility/
├── tools/
│   └── matlab/
│       └── buildOptimizedBusObjectFromModelBlock.m
├── tests/
└── docs/
    └── media/
        ├── demo.gif
        └── screenshot_main.png
```

---

## Installation

```bash
git clone https://github.com/<your-github-id>/realtime-vehicle-ai-validation-studio.git
cd realtime-vehicle-ai-validation-studio
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

If Qt style rendering behaves differently on a local Windows machine, the stylesheet can be disabled for debugging:

```cmd
set E2E_MOCK_DISABLE_QSS=1
python main.py
```

---

## Building the C++ Mock Backend

```bash
cd _backend/cpp
cmake -S . -B build
cmake --build build
```

The Python GUI does not require the C++ executable to run. The C++ mock exists to demonstrate backend structure and C++ implementation capability.

---

## Running the MATLAB Mock Utility

Open MATLAB, add the repository root to the MATLAB path, then call:

```matlab
[busObj, report] = buildOptimizedBusObjectFromModelBlock( ...
    "demo_model/AI_Input_Interface", ...
    "AI_Input_OptimizedBus", ...
    "ApplyToModel", true);
```

This is a mock utility script. It is intended to demonstrate the workflow concept and may require adaptation for a real Simulink model, real code generation settings, and a real company-specific modeling guideline.

---

## Architecture Overview

```text
+----------------------------------------------------------+
| MATLAB / Simulink MBD Layer                              |
| - find non-virtual bus creators                          |
| - inspect connected signal data types                    |
| - generate optimized Simulink.Bus object                 |
| - apply optimized order back into the model              |
| - generated C struct layout concept                      |
+--------------------------+-------------------------------+
                           |
                           v
+----------------------------------------------------------+
| PyQt5 Frontend                                           |
| - signal list                                            |
| - validation canvas                                      |
| - model configuration dialog                             |
| - pyqtgraph monitors                                     |
+--------------------------+-------------------------------+
                           |
                           v
+----------------------------------------------------------+
| Backend Interface / Transport Abstraction                |
| - mock backend                                           |
| - CAN-FD/XCP-style adapter concept                       |
| - future Ethernet adapter extension point                |
+--------------------------+-------------------------------+
                           |
                           v
+----------------------------------------------------------+
| Mock Data / Metadata Layer                               |
| - synthetic A2L                                          |
| - synthetic ELF symbols                                  |
| - synthetic replay data                                  |
| - placeholder model files                                |
+----------------------------------------------------------+
```

The frontend does not depend on a single hardware transport. The backend layer is designed as an adapter boundary so the transport can evolve independently from the validation UI.

---

## Public-Safe Mock Policy

This repository intentionally avoids:

- production ECU data
- real A2L files
- real ELF files
- internal Simulink model paths
- internal bus object definitions
- internal signal names
- internal memory addresses
- proprietary model files
- company-specific validation logic
- hardware-specific confidential implementation details

The following are synthetic:

- signal names
- signal descriptions
- ECU addresses
- Simulink paths
- bus object names
- replay values
- model names
- model outputs
- backend packets
- graph data
- timing values

---

## What This Project Demonstrates

- MATLAB/Simulink MBD workflow understanding
- auto-code-generation-oriented signal interface preparation
- non-virtual bus and external/global interface concept
- embedded C struct layout and data alignment awareness
- automatic bus object generation
- applying optimized bus ordering back into a Simulink model
- PyQt5 desktop tool development
- C++ backend mock implementation
- GUI/backend separation
- transport-adaptable architecture
- real-time signal visualization
- block-diagram UI design
- dynamic model I/O configuration
- port-based connection modeling
- async replay simulation
- pyqtgraph-based monitoring
- public-safe portfolio packaging

---

## Limitations

This is a mock portfolio project.

It does not:

- connect to a real ECU
- perform real XCP communication
- perform real Ethernet measurement
- parse production A2L/ELF files
- include real Simulink models
- run proprietary AI models
- guarantee hard real-time timing
- represent any confidential production tool

---

## License / Usage

This repository is provided as a public-safe portfolio demonstration.

No open-source license is currently granted.  
All rights are reserved by the author unless explicitly stated otherwise.

You may view this repository for portfolio and evaluation purposes, but you may not copy, redistribute, modify, or use the code, architecture, assets, or documentation for commercial or production purposes without written permission.

---

## Roadmap

Possible future extensions:

- Ethernet transport adapter mock
- SOME/IP-style replay adapter
- MDF4/BLF log replay support
- ONNX Runtime integration
- model input/output schema validation
- save/load canvas layout
- node grouping
- signal unit conversion editor
- replay timeline scrubber
- validation rule engine
- automated report export
- Simulink model advisor-style interface checks
- bus object diff/report generation
- generated C struct packing report

---

## Suggested GitHub Topics

```text
pyqt5
cpp
matlab
simulink
model-based-design
embedded-c
vehicle-ai
adas
real-time-visualization
signal-processing
model-validation
mock-data
portfolio-project
transport-abstraction
```

---

## Author

Created as a public-safe engineering portfolio project by Jaewoong Hwang.
