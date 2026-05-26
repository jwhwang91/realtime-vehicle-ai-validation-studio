#include "xcp_protocol.h"
#include <iomanip>
#include <iostream>

bool configure_mock_xcp_session(const BackendConfig& cfg) {
    std::cout << "[mock-xcp] CONNECT OK" << std::endl;
    std::cout << "[mock-xcp] transport=" << cfg.transport
              << ", cycle_ms=" << cfg.cycle_ms
              << ", measurements=" << cfg.measurements.size()
              << ", characteristics=" << cfg.characteristics.size()
              << std::endl;

    for (const auto& odt : cfg.odt_layout) {
        std::cout << "[mock-xcp] ODT " << odt.odt_id << " packed order:" << std::endl;
        for (const auto& sig : odt.signals) {
            std::cout << "  - " << sig.name
                      << " addr=0x" << std::hex << std::uppercase << sig.address << std::dec
                      << " type=" << data_type_to_string(sig.data_type)
                      << " bytes=" << data_type_size_bytes(sig.data_type)
                      << std::endl;
        }
    }
    return true;
}
