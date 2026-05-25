# Real-Time Vehicle AI Validation Studio

> [!NOTE]
> This repository is a **public-safe portfolio mock**.  
> It does **not** contain proprietary company code, real ECU data, production A2L/ELF files, internal model assets, or confidential validation logic.  
> All signals, addresses, replay values, model files, and backend data paths are synthetic.

A transport-adaptable **PyQt5 + C++ vehicle AI validation studio mock** for real-time vehicle signal replay, AI model block validation, and data-flow visualization.

This project demonstrates a public-facing version of a vehicle AI validation workflow originally designed under constrained hardware conditions. The available communication path was CAN-FD/XCP-style access, but the backend was intentionally separated behind a transport abstraction layer so that future Ethernet-based interfaces can be integrated without redesigning the UI, signal workflow, or model validation canvas.

---

## Repository Description

**Public-safe portfolio version of a transport-adaptable real-time vehicle AI validation studio using synthetic A2L, ELF, replay, and model data.**

---

## Demo

A working GIF or short video can be placed here.

### Preview GIF

```markdown
![Working demo](docs/media/demo.gif)
```

### Preview Video

```markdown
https://github.com/<your-github-id>/realtime-vehicle-ai-validation-studio/assets/<asset-id>/<video-file>
```

Recommended demo flow to record:

1. Launch the PyQt5 application.
2. Load the mock A2L/ELF metadata.
3. Drag measurement signals from the left panel into the canvas.
4. Add an empty model block.
5. Double-click the model block and configure:
   - `.py` script or `.onnx` model path
   - input count
   - output count
6. Connect signal ports to model ports using click-to-connect.
7. Press **Start**.
8. Show real-time line activation, where flowing data turns the connection line white.
9. Open **ALL Graph** and show floating pyqtgraph windows.
10. Double-click an individual connection line and show the real-time data-flow graph.
11. Use Ctrl multi-select or rubber-band selection to move/delete multiple blocks.

Suggested media location:

```text
docs/
└── media/
    ├── demo.gif
    └── demo.mp4
```

---

## Why This Project Exists

Vehicle AI validation workflows often depend on specific hardware, ECU interfaces, calibration files, and internal toolchains. In the original engineering context, the available hardware path was limited, so the system was designed to extract the maximum practical value from the available interface while keeping the software architecture expandable.

The key design decision was to separate the GUI and validation workflow from the transport backend.

Instead of hard-coding the application around one interface type, the project uses a backend abstraction layer:

```text
_backend/
├── mock backend
├── CAN-FD / XCP-style adapter concept
└── future Ethernet adapter extension point
```

This allows the same UI and model workflow to support different transport implementations later, including Ethernet-based measurement or calibration interfaces.

---

## Core Features

### 1. Simulink-like Validation Canvas

The central canvas behaves like a lightweight block-diagram editor.

Supported interactions:

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

### 2. Dynamic Model Blocks

Model blocks can be configured at runtime.

Double-click a model block to open the configuration dialog:

- Select `.py` script or `.onnx` model file.
- Set input count.
- Set output count.
- The block graphically updates its input/output ports.
- Existing invalid connections are pruned when port count is reduced.

### 3. Independent Port Connections

Each model input/output has its own graphical port.

This avoids unrealistic behavior where every signal connects to a single shared node port. Each connection stores:

```text
source block
source port index
destination block
destination port index
data key
```

### 4. Real-Time Data-Flow Visualization

During replay:

- Active connection lines turn white.
- Inactive connection lines remain green.
- Selected inactive lines are highlighted.
- Double-clicking a line opens a floating pyqtgraph window for real-time data-flow monitoring.

### 5. Floating Graph Windows with pyqtgraph

The **ALL Graph** button opens floating real-time graphs.

Example graph groups:

- DAQ / measurement signals
- model output values
- ECU write value
- jitter / replay timing metrics

### 6. Mock A2L and ELF Integration

The project includes public-safe mock metadata:

- synthetic A2L signal definitions
- synthetic ELF symbol map
- synthetic signal addresses
- synthetic measurement and characteristic data

No real ECU calibration metadata is included.

### 7. C++ Mock Backend

The repository includes a buildable C++ mock backend to show embedded/backend implementation ability.

The C++ code is intentionally mock-only and does not communicate with real hardware.

It demonstrates:

- backend process structure
- signal packet generation
- mock shared-memory style data exchange concept
- CMake-based build flow
- separation between frontend and backend responsibilities

---

## Tech Stack

| Area | Technology |
|---|---|
| GUI | PyQt5 |
| Real-time plotting | pyqtgraph |
| Backend mock | Python async worker |
| C++ backend mock | C++17 |
| Build system | CMake |
| Data files | Synthetic A2L, ELF, CSV-style replay |
| Architecture pattern | Transport-adaptable backend abstraction |
| Purpose | Public-safe portfolio demo |

---

## Project Structure

```text
realtime-vehicle-ai-validation-studio/
├── main.py
├── requirements.txt
├── README.md
│
├── _uiux/
│   ├── main_handler.py
│   ├── canvas_scene.py
│   ├── dialogs.py
│   ├── plot_window.py
│   ├── searchable_list.py
│   └── styles/
│
├── _backend/
│   ├── __init__.py
│   ├── interface.py
│   ├── mock_backend.py
│   ├── transport/
│   ├── mock_assets/
│   │   ├── mock_signals.a2l
│   │   ├── mock_symbols.elf.txt
│   │   ├── mock_replay.csv
│   │   └── models/
│   │       ├── timeseriesAI_model1.py
│   │       └── placeholder_model.onnx
│   │
│   └── cpp/
│       ├── CMakeLists.txt
│       ├── include/
│       ├── src/
│       └── vendor/
│
├── _utility/
│   ├── a2l_parser.py
│   ├── elf_symbol_parser.py
│   └── mock_data.py
│
├── tests/
│   └── test_mock_assets.py
│
└── docs/
    └── media/
        ├── demo.gif
        └── demo.mp4
```

The exact file names may vary slightly depending on the current mock version, but the repository is organized around this structure.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-github-id>/realtime-vehicle-ai-validation-studio.git
cd realtime-vehicle-ai-validation-studio
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

If Qt style rendering behaves differently on a local Windows machine, the stylesheet can be disabled for debugging:

Windows CMD:

```cmd
set E2E_MOCK_DISABLE_QSS=1
python main.py
```

PowerShell:

```powershell
$env:E2E_MOCK_DISABLE_QSS="1"
python main.py
```

---

## Building the C++ Mock Backend

The C++ backend is included as a public-safe mock implementation.

```bash
cd _backend/cpp
cmake -S . -B build
cmake --build build
```

The Python GUI does not require the C++ executable to run. The C++ mock exists to demonstrate backend structure and C++ implementation capability.

Optional external backend launch can be controlled through an environment variable if supported by the current version:

```bash
E2E_MOCK_LAUNCH_CPP=1 python main.py
```

On Windows CMD:

```cmd
set E2E_MOCK_LAUNCH_CPP=1
python main.py
```

---

## Usage Guide

### Add a measurement block

1. Select the **MEASUREMENT** tab.
2. Drag a signal into the canvas.
3. The signal appears as a block with metadata from the mock A2L file.

### Add a characteristic block

1. Select the **CHARACTERISTIC** tab.
2. Drag a characteristic item into the canvas.
3. The block appears as a mock ECU write/output target.

### Add a model block

1. Click **Add Model**.
2. An empty model block appears on the canvas.
3. Double-click the model block.
4. Select a `.py` or `.onnx` file.
5. Set input/output counts.
6. Confirm the configuration.

### Connect blocks

1. Click a source output port.
2. Move the mouse to a destination input port.
3. Click the destination port.
4. A connection line is created.

Cancel connection:

- Press `Esc`, or
- Right-click the canvas.

### Monitor data flow

- Press **Start** to begin synthetic replay.
- Active data-flow lines turn white.
- Press **ALL Graph** to open floating graph windows.
- Double-click an individual connection line to inspect its data-flow graph.

### Multi-select blocks

- Hold `Ctrl` and click blocks to add/remove selection.
- Drag over an empty canvas area to rubber-band select blocks.
- Drag one selected block to move the selected group.
- Press `Delete` or `Backspace` to delete all selected blocks.

---

## Architecture Overview

The application is intentionally split into separate layers.

```text
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
- internal signal names
- internal memory addresses
- proprietary model files
- company-specific validation logic
- hardware-specific confidential implementation details

The following are synthetic:

- signal names
- signal descriptions
- ECU addresses
- replay values
- model names
- model outputs
- backend packets
- graph data
- timing values

---

## What This Project Demonstrates

This project is intended to demonstrate the following engineering capabilities:

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
- ability to convert an internal engineering idea into a sanitized demo product

---

## Limitations

This is a mock portfolio project.

It does not:

- connect to a real ECU
- perform real XCP communication
- perform real Ethernet measurement
- parse production A2L/ELF files
- run proprietary AI models
- guarantee hard real-time timing
- represent any confidential production tool

---

## License / Usage

This repository is provided as a public-safe portfolio demonstration.

No open-source license is currently granted.  
All rights are reserved by the author unless explicitly stated otherwise.

You may view this repository for portfolio and evaluation purposes, but you may not copy, redistribute, modify, or use the code, architecture, assets, or documentation for commercial or production purposes without written permission.

This project does not contain proprietary company code, real ECU data, production A2L/ELF files, internal model assets, or confidential validation logic. All data and assets are synthetic.

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

---

## Suggested GitHub Topics

```text
pyqt5
cpp
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
