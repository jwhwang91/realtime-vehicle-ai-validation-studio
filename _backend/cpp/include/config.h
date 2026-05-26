#pragma once
#include <cstdint>
#include <string>
#include <vector>

enum class SignalRole : uint8_t {
    Measurement = 0,
    Characteristic = 1,
    InternalModel = 2
};

enum class DataType : uint8_t {
    Float64 = 0,
    Float32 = 1,
    UInt32 = 2,
    Int32 = 3,
    UInt16 = 4,
    Int16 = 5,
    UInt8 = 6,
    Int8 = 7,
    Boolean = 8
};

struct SigDescriptor {
    std::string name;
    uint32_t address = 0;
    std::string unit;
    bool writable = false;
    DataType data_type = DataType::Float32;
    SignalRole role = SignalRole::Measurement;
    double min_value = 0.0;
    double max_value = 1.0;
    std::string description;
};

struct OdtChunk {
    uint16_t odt_id = 0;
    std::vector<SigDescriptor> signals;
};

struct BackendConfig {
    std::string transport = "MOCK_CANFD_XCP";
    uint32_t cycle_ms = 20;
    uint32_t max_cycles = 250;
    uint32_t print_every = 25;
    std::vector<SigDescriptor> measurements;
    std::vector<SigDescriptor> characteristics;
    std::vector<OdtChunk> odt_layout;
};

BackendConfig load_mock_config();
std::string data_type_to_string(DataType type);
std::string role_to_string(SignalRole role);
uint32_t data_type_size_bytes(DataType type);
