#include "config.h"
#include <algorithm>
#include <cctype>

namespace {

uint16_t datatype_size(const std::string& datatype) {
    std::string dt = datatype;
    std::transform(dt.begin(), dt.end(), dt.begin(), [](unsigned char c){ return static_cast<char>(std::toupper(c)); });
    if (dt.find("DOUBLE") != std::string::npos || dt.find("64") != std::string::npos) return 8;
    if (dt.find("FLOAT") != std::string::npos || dt.find("32") != std::string::npos || dt == "SLONG" || dt == "ULONG") return 4;
    if (dt.find("16") != std::string::npos || dt == "UWORD" || dt == "SWORD") return 2;
    return 1;
}

} // namespace

BackendConfig load_mock_config() {
    BackendConfig cfg;
    cfg.cycle_ms = 16;
    cfg.measurements = {
        {"signal1", 0x10100000u, "ULONG", "deg", "mock_symbol_01", false},
        {"signal2", 0x10100010u, "SLONG", "m/s", "mock_symbol_02", false},
        {"signal3", 0x10100020u, "UWORD", "arb", "mock_symbol_03", false},
        {"signal4", 0x10100030u, "UBYTE", "deg", "mock_symbol_04", false},
        {"signal5", 0x10100040u, "FLOAT32_IEEE", "m/s", "mock_symbol_05", false},
        {"signal6", 0x10100050u, "SLONG", "arb", "mock_symbol_06", false},
    };
    cfg.characteristics = {
        {"signal7", 0x10100060u, "ULONG", "deg", "mock_symbol_07", true},
        {"signal8", 0x10100070u, "UWORD", "m/s", "mock_symbol_08", true},
        {"ecu_write_value", 0xB004342Bu, "FLOAT32_IEEE", "arb", "mock_symbol_ecu_write", true},
    };
    return cfg;
}

BackendConfig load_mock_config_from_json(const std::string& runtime_json) {
    // Public mock note:
    // The real backend would parse runtime_json from SHM and create DAQ/STIM
    // lists from the selected canvas signals.  To keep this mock dependency-free
    // and buildable everywhere, we keep default synthetic signals and store the
    // raw JSON for logging/review.
    BackendConfig cfg = load_mock_config();
    cfg.runtime_json = runtime_json;
    return cfg;
}

std::vector<OdtChunk> build_mock_odt_chunks(const BackendConfig& cfg, uint16_t max_payload_bytes) {
    std::vector<SigDescriptor> sorted = cfg.measurements;
    std::sort(sorted.begin(), sorted.end(), [](const SigDescriptor& a, const SigDescriptor& b) {
        return datatype_size(a.datatype) > datatype_size(b.datatype);
    });

    std::vector<OdtChunk> chunks;
    OdtChunk current;
    uint16_t used = 0;
    uint16_t odt_id = 0;

    for (const auto& sig : sorted) {
        const uint16_t sz = datatype_size(sig.datatype);
        if (!current.signals.empty() && used + sz > max_payload_bytes) {
            current.odt_id = odt_id++;
            chunks.push_back(current);
            current = OdtChunk{};
            used = 0;
        }
        current.signals.push_back(sig);
        used = static_cast<uint16_t>(used + sz);
    }

    if (!current.signals.empty()) {
        current.odt_id = odt_id++;
        chunks.push_back(current);
    }
    return chunks;
}
