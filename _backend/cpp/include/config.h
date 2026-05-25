#pragma once
#include <cstdint>
#include <string>
#include <vector>

struct SigDescriptor {
    std::string name;
    uint32_t address = 0;
    std::string unit;
    bool writable = false;
};

struct OdtChunk {
    uint16_t odt_id = 0;
    std::vector<SigDescriptor> signals;
};

struct BackendConfig {
    std::string transport = "MOCK_CANFD_XCP";
    uint32_t cycle_ms = 50;
    std::vector<SigDescriptor> measurements;
    std::vector<SigDescriptor> characteristics;
};

BackendConfig load_mock_config();
