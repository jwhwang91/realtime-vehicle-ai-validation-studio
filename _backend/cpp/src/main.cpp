#include "config.h"
#include "shm_layout.h"
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iostream>
#include <thread>

extern bool open_mock_vector_channel();
extern bool configure_mock_xcp_session(const BackendConfig& cfg);
extern void write_mock_daq_snapshot(ShmDataBlock& block, double t, uint64_t ts);
extern void consume_mock_stim_snapshot(const ShmDataBlock& out);

static uint64_t now_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    std::cout << "xcp_backend mock executable - public portfolio build" << std::endl;
    if (!open_mock_vector_channel()) {
        std::cerr << "failed to open mock channel" << std::endl;
        return 2;
    }
    BackendConfig cfg = load_mock_config();
    configure_mock_xcp_session(cfg);

    MockShmBlock shm;
    std::strncpy(shm.control.status.data(), "mock running", shm.control.status.size() - 1);
    shm.control.run_state.store(1);

    for (uint64_t tick = 0; tick < 200; ++tick) {
        const double t = static_cast<double>(tick) * static_cast<double>(cfg.cycle_ms) / 1000.0;
        write_mock_daq_snapshot(shm.shm_in, t, now_us());
        shm.control.tick_count = tick;
        if (tick % 20 == 0) {
            std::cout << "[mock-backend] tick=" << tick
                      << " signal1=" << shm.shm_in.signals[0].value
                      << " signal4=" << shm.shm_in.signals[3].value
                      << std::endl;
        }
        consume_mock_stim_snapshot(shm.shm_out);
        std::this_thread::sleep_for(std::chrono::milliseconds(cfg.cycle_ms));
    }
    shm.control.run_state.store(0);
    std::cout << "xcp_backend mock stopped" << std::endl;
    return 0;
}
