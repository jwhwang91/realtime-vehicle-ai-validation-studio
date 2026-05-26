#include "config.h"
#include <algorithm>

std::string data_type_to_string(DataType type) {
    switch (type) {
        case DataType::Float64: return "double";
        case DataType::Float32: return "single";
        case DataType::UInt32: return "uint32";
        case DataType::Int32: return "int32";
        case DataType::UInt16: return "uint16";
        case DataType::Int16: return "int16";
        case DataType::UInt8: return "uint8";
        case DataType::Int8: return "int8";
        case DataType::Boolean: return "boolean";
        default: return "unknown";
    }
}

std::string role_to_string(SignalRole role) {
    switch (role) {
        case SignalRole::Measurement: return "MEASUREMENT";
        case SignalRole::Characteristic: return "CHARACTERISTIC";
        case SignalRole::InternalModel: return "INTERNAL_MODEL";
        default: return "UNKNOWN";
    }
}

uint32_t data_type_size_bytes(DataType type) {
    switch (type) {
        case DataType::Float64: return 8;
        case DataType::Float32:
        case DataType::UInt32:
        case DataType::Int32: return 4;
        case DataType::UInt16:
        case DataType::Int16: return 2;
        case DataType::UInt8:
        case DataType::Int8:
        case DataType::Boolean: return 1;
        default: return 4;
    }
}

BackendConfig load_mock_config() {
    BackendConfig cfg;
    cfg.transport = "MOCK_CANFD_XCP_STYLE";
    cfg.cycle_ms = 20;
    cfg.max_cycles = 250;
    cfg.print_every = 25;

    cfg.measurements = {
        {"signal1", 0x10100000u, "km/h", false, DataType::UInt32, SignalRole::Measurement, 0.0, 250.0, "Synthetic vehicle speed"},
        {"signal2", 0x10100010u, "m/s^2", false, DataType::Float32, SignalRole::Measurement, -10.0, 10.0, "Synthetic longitudinal acceleration"},
        {"signal3", 0x10100020u, "rad/s", false, DataType::Float32, SignalRole::Measurement, -1.0, 1.0, "Synthetic yaw rate"},
        {"signal4", 0x10100030u, "deg", false, DataType::UInt16, SignalRole::Measurement, -720.0, 720.0, "Synthetic steering angle"},
        {"signal5", 0x10100040u, "%", false, DataType::UInt8, SignalRole::Measurement, 0.0, 100.0, "Synthetic confidence"},
        {"signal6", 0x10100050u, "bool", false, DataType::Boolean, SignalRole::Measurement, 0.0, 1.0, "Synthetic validity flag"},
    };

    cfg.characteristics = {
        {"signal7", 0x10100060u, "gain", true, DataType::Float32, SignalRole::Characteristic, 0.0, 10.0, "Synthetic writable characteristic"},
        {"signal8", 0x10100070u, "offset", true, DataType::Float32, SignalRole::Characteristic, -5.0, 5.0, "Synthetic writable characteristic"},
        {"ecu_write_value", 0xB004342Bu, "arb", true, DataType::Float32, SignalRole::Characteristic, 0.0, 1.0, "Synthetic ECU write target"},
    };

    // A mock ODT grouping that resembles how a DAQ list could be packed.
    OdtChunk odt0;
    odt0.odt_id = 0;
    odt0.signals = cfg.measurements;
    std::sort(odt0.signals.begin(), odt0.signals.end(), [](const auto& a, const auto& b) {
        return data_type_size_bytes(a.data_type) > data_type_size_bytes(b.data_type);
    });
    cfg.odt_layout.push_back(odt0);

    return cfg;
}
