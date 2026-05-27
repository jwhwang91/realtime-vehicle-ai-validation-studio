#pragma once
#include <cstdint>
#include <string>
#include <vector>

struct SigDescriptor {
    std::string name;
    uint32_t address = 0;
    std::string datatype = "UNKNOWN";
    std::string unit;
    std::string symbol;
    bool writable = false;
};

struct OdtChunk {
    uint16_t odt_id = 0;
    std::vector<SigDescriptor> signals;
};

struct BackendConfig {
    std::string transport = "MOCK_CANFD_XCP";
    uint32_t cycle_ms = 50;
    std::string runtime_json;
    std::vector<SigDescriptor> measurements;
    std::vector<SigDescriptor> characteristics;
};

BackendConfig load_mock_config();
BackendConfig load_mock_config_from_json(const std::string& runtime_json);
std::vector<OdtChunk> build_mock_odt_chunks(const BackendConfig& cfg, uint16_t max_payload_bytes = 48);
