# Real-Time Vehicle AI Validation Studio

> [!NOTE]
> This repository is a **public-safe portfolio mock**.  
> It does **not** contain proprietary company code, real ECU data, production A2L/ELF files, internal model assets, confidential validation logic, hardware channel settings, real CAN identifiers, or production Simulink models.  
> All signals, addresses, replay values, model files, Simulink paths, bus objects, runtime JSON payloads, and backend data paths are synthetic.

A transport-adaptable **PyQt5 + C++ + MATLAB/Simulink vehicle AI validation studio mock** for real-time vehicle signal replay, AI model block validation, MBD-oriented signal interface preparation, SHM-based frontend/backend configuration exchange, and data-flow visualization.

This project demonstrates a public-facing version of a vehicle AI validation workflow originally designed under constrained hardware conditions. The available communication path was CAN-FD/XCP-style access, but the backend was intentionally separated behind a transport abstraction layer so that future Ethernet-based interfaces can be integrated without redesigning the UI, signal workflow, model validation canvas, SHM protocol, or MBD preparation utilities.

---

## Repository Description

**Public-safe portfolio version of a transport-adaptable real-time vehicle AI validation studio using synthetic A2L, ELF, replay, model, MATLAB/Simulink MBD utility data, and SHM-based runtime configuration exchange.**

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

---

## Architecture Documents

Public-safe architecture documentation is included here:

- [View interactive architecture document](https://jwhwang91.github.io/realtime-vehicle-ai-validation-studio/architecture_public.html)
- [View source HTML](docs/architecture_public.html)

`architecture_public.html` contains block diagrams for the overall system, runtime data flow, C++ backend, SHM JSON bridge, MATLAB/Simulink bus optimization, and PyQt5 validation canvas.

`shm_runtime_protocol.md` describes how the frontend exports the current canvas state as runtime JSON and how the backend reads that configuration through a shared-memory-style boundary.

---

## Why This Project Exists

Vehicle AI validation workflows often depend on specific hardware, ECU interfaces, calibration files, MATLAB/Simulink MBD workflows, auto-generated embedded C code, and internal toolchains.

In the original engineering context, the available hardware path was limited. If Ethernet measurement hardware had been available, the preferred validation path would have been Ethernet-based due to better throughput and scalability. However, under the available equipment constraints, the practical interface path was CAN-FD/XCP-style measurement and calibration access.

Because of that constraint, the system needed to extract the maximum value from the available communication path while keeping the software architecture expandable.

The key design decision was to separate the GUI and validation workflow from the transport backend:

```text
_backend/
├── mock backend
├── SHM runtime config bridge
├── CAN-FD / XCP-style adapter concept
└── future Ethernet adapter extension point
```

This allows the same UI and model workflow to support different transport implementations later, including Ethernet-based measurement or calibration interfaces.

---

## Intended Runtime Flow

The important runtime concept is that the frontend does not simply start a fixed backend.

The user builds the validation workflow on the PyQt canvas first:

```text
drag MEASUREMENT blocks
drag CHARACTERISTIC blocks
add model blocks
load .py / .onnx model files
connect ports
press Start
```

When **Start** is pressed, the Python frontend exports the current canvas state into a runtime JSON configuration.

That runtime JSON contains the information the backend needs to configure the acquisition/write-back loop:

```text
XCP / transport settings
selected measurement signals
selected characteristic targets
signal addresses
data types
units
model blocks
model file paths
node graph
edge graph
DAQ/STIM setup inputs
```

The runtime JSON is written into a shared-memory-style configuration block. The C++ backend reads that config block, builds the DAQ/STIM setup concept, runs the real-time acquisition loop, and publishes the latest values back through a shared-memory-style data snapshot.

In the public mock, all of this uses synthetic data and a mock SHM emulator. In the internal concept, this boundary represented the path from Python UI configuration to a C++ backend connected to a development ECU through a VN-series CAN-FD interface.

```text
PyQt canvas state
→ runtime JSON config
→ SHM config block
→ C++ backend reads config
→ DAQ/STIM setup concept
→ VN-series CAN-FD / development ECU path in internal prototype
→ realtime measurement values
→ SHM data snapshot
→ PyQt canvas + pyqtgraph monitors
```

---

## SHM JSON Runtime Config Bridge

The SHM bridge is the boundary that makes the frontend/backend separation practical.

### Frontend-to-backend direction

```text
Python frontend
→ collect current canvas graph
→ build runtime JSON payload
→ write JSON into SHM config block using seqlock-style sequence convention
→ backend sees new config sequence
```

### Backend-to-frontend direction

```text
C++ backend
→ read runtime JSON config
→ configure synthetic DAQ/STIM loop
→ publish latest signal/model/output values into SHM data block
→ frontend reads latest coherent snapshot
→ canvas lines, block values, and pyqtgraph windows update
```

The mock version is intentionally implemented without real hardware access, but the interface shape mirrors the intended production-style split.

---

## Development Timeline

This mock project represents a public-safe version of an internal engineering concept that was designed, prototyped, stabilized, and translated into a C++-oriented backend structure within approximately **three months**.

```text
architecture definition
→ Python backend rapid prototype
→ hardware-backed feasibility check with VN-series CAN-FD interface and development ECU
→ CAN-FD/XCP-style DAQ/STIM loop validation
→ timing, parsing, and frontend/backend data exchange refinement
→ SHM runtime config bridge concept
→ stabilized backend architecture
→ C++ mock backend port
→ public-safe PyQt5/C++/MATLAB portfolio packaging
```

---

## Engineering Impact

The original concept helped support an AI-transition workflow under constrained hardware conditions.

Instead of waiting for scarce or unavailable Ethernet-based measurement equipment, the system was designed to make practical use of the available CAN-FD/XCP-style path while keeping the backend extensible for future Ethernet integration.

This allowed AI-model input signal flows to be prepared and validated earlier with existing equipment, while preserving a software architecture that could later migrate to a higher-throughput transport layer.

In this public repository, the impact is represented through synthetic data, mock transports, mock A2L/ELF files, mock SHM protocol, and sanitized UI/backend logic.

---

## Hardware-Backed Python Prototype

Before translating the backend structure into C++, the initial backend concept was validated through a Python prototype.

The internal prototype used a **Vector VN-series CAN-FD interface connected to a development ECU** to validate the XCP-style acquisition loop, signal parsing behavior, timing characteristics, and frontend/backend data exchange.

The public repository does not include hardware-specific channel settings, real CAN identifiers, production A2L/ELF files, ECU memory addresses, or proprietary signal names. The hardware-backed workflow is represented through mock transports, runtime JSON payloads, and synthetic data.

---

## AI-Assisted Development Workflow

This project followed an **architecture-first, AI-assisted development workflow**.

I first defined the system architecture, signal flow, backend abstraction, UI behavior, SHM runtime config bridge, MBD preparation concept, validation requirements, and public-safe boundaries. To reduce implementation risk, I initially built a Python backend prototype using CAN-style communication libraries and mock XCP/DAQ concepts. The internal prototype was validated with a VN-series CAN-FD interface connected to a development ECU, which allowed the XCP-style DAQ loop, signal parsing structure, timing behavior, and frontend/backend data exchange to be checked before the C++ port.

After the backend behavior was validated and stabilized, the same architecture was translated into a C++ mock backend to better represent a production-oriented embedded toolchain.

AI coding agents were used as implementation accelerators for prototyping, refactoring, UI iteration, SHM bridge implementation, and C++ translation. The architecture decisions, validation strategy, debugging direction, public-safe sanitization, and final integration were engineer-owned.

---

## MBD / Simulink Code Generation Context

The production-style development workflow behind this mock is based on MATLAB/Simulink Model-Based Design.

```text
Simulink model
→ auto code generation
→ generated C code
→ ECU flash
→ runtime measurement / calibration / validation
```

For AI validation, the input signals required by the AI model must be exposed in a predictable embedded memory layout after code generation.

---

## Power of the MATLAB Bus Optimization Utility

```text
tools/matlab/buildOptimizedBusObjectFromModelBlock.m
```

The utility is designed to:

1. Automatically find non-virtual buses inside a Simulink model.
2. Read connected signal data types automatically.
3. Create a padding-aware optimized `Simulink.Bus` object in the MATLAB workspace.
4. Apply the optimized signal order back into the Simulink model.

```text
optimized Simulink bus connection order
→ optimized Simulink.Bus object
→ generated C struct field order
→ more predictable A2L/ELF-style runtime access
→ easier real-time validation under CAN-FD/XCP constraints
```

---

## Core Features

### Simulink-like Validation Canvas

- Drag/drop signals from the A2L signal list.
- Add model blocks.
- Move blocks freely.
- Ctrl-click and rubber-band multi-select.
- Delete selected blocks with `Delete` or `Backspace`.
- Middle-mouse panning.
- Click-to-connect port wiring.
- Cancel pending connection with `Esc` or right-click.

### Dynamic Model Blocks

- Select `.py` script or `.onnx` model file.
- Set input count and output count.
- Graphically update model input/output ports.
- Prune invalid old connections when port count is reduced.

### Runtime Config Export

- Export active canvas nodes and edges.
- Include selected measurements and characteristics.
- Include model block metadata and model file paths.
- Build backend runtime JSON.
- Write runtime JSON into SHM config block.

### Real-Time Data-Flow Visualization

- Active connection lines turn white.
- Double-clicking a line opens a floating pyqtgraph window.
- **ALL Graph** opens floating real-time graphs.

### C++ Mock Backend

The C++ backend is structured around:

```text
transport abstraction
runtime JSON config reader
synthetic DAQ acquisition
synthetic STIM/write-back path
signal database
staged model pipeline
shared-memory-style config/data blocks
realtime loop with jitter metrics
```

---

## Tech Stack

| Area | Technology |
|---|---|
| MBD workflow | MATLAB / Simulink |
| Auto code generation concept | Simulink Coder / Embedded Coder-style workflow |
| Embedded interface concept | Generated C struct / external global data |
| MBD automation utility | MATLAB script for non-virtual bus detection, data-type sorting, and Simulink bus rewiring |
| Hardware-backed prototype context | VN-series CAN-FD interface + development ECU validation |
| Rapid backend prototype | Python, CAN-style communication libraries, mock XCP/DAQ concepts |
| Runtime configuration exchange | JSON payload over shared-memory-style config block |
| Data snapshot exchange | Shared-memory-style data block with seqlock convention |
| GUI | PyQt5 |
| Real-time plotting | pyqtgraph |
| Backend mock | Python async worker |
| C++ backend mock | C++17 |
| Build system | CMake |
| Data files | Synthetic A2L, ELF, CSV-style replay |
| Architecture pattern | Transport-adaptable backend abstraction |
| Communication constraint represented | CAN-FD / XCP-style access |
| Future extension point | Ethernet transport adapter |
| Development approach | Architecture-first, AI-assisted rapid prototyping and C++ porting |
| Timeline represented | Approximately 3-month concept-to-working-tool workflow |
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
│   ├── _shared_memory.py
│   ├── mock_assets/
│   └── cpp/
├── _utility/
├── tools/
│   └── matlab/
│       └── buildOptimizedBusObjectFromModelBlock.m
├── tests/
└── docs/
    ├── architecture_public.html
    ├── shm_runtime_protocol.md
    └── media/
        ├── demo.gif
        └── screenshot_main.png
```

---

## Installation

```bash
git clone https://github.com/<your-github-id>/realtime-vehicle-ai-validation-studio.git
cd realtime-vehicle-ai-validation-studio
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

```bat
:: Windows (cmd.exe)
python -m venv .venv
.venv\Scripts\activate.bat
```

Then install the dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

---

## Building the C++ Mock Backend

### Prerequisites

CMake 3.16 or newer must be installed and on `PATH`, along with a C++17 compiler.

```bash
# macOS
brew install cmake

# Ubuntu / Debian
sudo apt install cmake build-essential

# Windows
winget install Kitware.CMake
```

Verify with `cmake --version`. If CMake is missing, `build_cpp.py` fails with
`RuntimeError: CMake was not found on PATH.`

### Build

```bash
cd _backend/cpp
cmake -S . -B build
cmake --build build
```

Or from the repository root, using the helper that also resolves the executable path:

```bash
python build_cpp.py
```

The Python GUI can run with the mock backend. The C++ backend exists to demonstrate the intended production-oriented backend structure and runtime SHM protocol boundary.

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
- real CAN identifiers
- hardware channel settings
- proprietary model files
- company-specific validation logic
- hardware-specific confidential implementation details
- actual team/project identifiers

The following are synthetic:

- signal names
- signal descriptions
- ECU addresses
- Simulink paths
- bus object names
- runtime JSON payload examples
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
- architecture-first engineering workflow
- approximately 3-month concept-to-working-tool execution
- Python rapid prototyping for backend feasibility validation
- hardware-backed feasibility validation with a VN-series CAN-FD interface and development ECU
- SHM-based runtime configuration and data snapshot exchange
- AI-assisted implementation acceleration with engineer-owned architecture
- C++ backend porting from validated backend structure
- PyQt5 desktop tool development
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

## License / Usage

This repository is provided as a public-safe portfolio demonstration.

No open-source license is currently granted.  
All rights are reserved by the author unless explicitly stated otherwise.

You may view this repository for portfolio and evaluation purposes, but you may not copy, redistribute, modify, or use the code, architecture, assets, or documentation for commercial or production purposes without written permission.

---

## Suggested GitHub Topics

```text
pyqt5
cpp
python
matlab
simulink
model-based-design
embedded-c
shared-memory
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
