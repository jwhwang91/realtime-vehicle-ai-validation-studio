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

    // ODT packing is derived from the DAQ list rather than stored on the config,
    // so setup logs exactly the layout the DAQ path will use.
    for (const auto& odt : build_mock_odt_chunks(cfg)) {
        std::cout << "[mock-xcp] ODT " << odt.odt_id << " packed order:" << std::endl;
        for (const auto& sig : odt.signals) {
            std::cout << "  - " << sig.name
                      << " addr=0x" << std::hex << std::uppercase << sig.address << std::dec
                      << " type=" << sig.datatype
                      << " bytes=" << datatype_size_bytes(sig.datatype)
                      << std::endl;
        }
    }
    return true;
}
