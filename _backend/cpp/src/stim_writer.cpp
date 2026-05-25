#include "shm_layout.h"
#include <iostream>

void consume_mock_stim_snapshot(const ShmDataBlock& out) {
    if (out.count == 0) return;
    std::cout << "[mock-stim] outputs=" << out.count << std::endl;
}
