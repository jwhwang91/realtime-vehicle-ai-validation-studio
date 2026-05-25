#include "config.h"
#include <iostream>

bool configure_mock_xcp_session(const BackendConfig& cfg) {
    std::cout << "[mock-xcp] CONNECT OK, measurements=" << cfg.measurements.size()
              << ", characteristics=" << cfg.characteristics.size() << std::endl;
    return true;
}
