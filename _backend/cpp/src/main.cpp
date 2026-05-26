#include "config.h"
#include "shm_layout.h"
#include "can_frame.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <thread>

extern bool configure_mock_xcp_session(const BackendConfig& cfg);
extern void write_mock_daq_snapshot(ShmDataBlock& block, const BackendConfig& cfg, uint32_t tick, uint64_t ts);
extern double evaluate_mock_model_pipeline(const ShmDataBlock& in, ModelStateBlock& model);
extern void write_mock_stim_snapshot(ShmDataBlock& out, const BackendConfig& cfg, double ecu_value, uint64_t ts);
extern void consume_mock_stim_snapshot(const ShmDataBlock& out);

static int arg_value(int argc, char** argv, const char* key, int fallback) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (std::string(argv[i]) == key) {
            return std::atoi(argv[i + 1]);
        }
    }
    return fallback;
}

static bool has_arg(int argc, char** argv, const char* key) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == key) return true;
    }
    return false;
}

static void print_help() {
    std::cout <<
        "xcp_backend mock executable - public portfolio build\n\n"
        "Options:\n"
        "  --cycles N       number of backend loop cycles, default 250\n"
        "  --period-ms N    loop period in ms, default from mock config\n"
        "  --print-every N  print status every N cycles, default 25\n"
        "  --help           show this help\n";
}

int main(int argc, char** argv) {
    if (has_arg(argc, argv, "--help")) {
        print_help();
        return 0;
    }

    std::cout << "xcp_backend mock executable - public portfolio build" << std::endl;
    std::cout << "No real ECU/A2L/ELF/XCP/Ethernet/company data is used." << std::endl;

    if (!open_mock_vector_channel()) {
        std::cerr << "failed to open mock channel" << std::endl;
        return 2;
    }

    BackendConfig cfg = load_mock_config();
    cfg.max_cycles = static_cast<uint32_t>(arg_value(argc, argv, "--cycles", static_cast<int>(cfg.max_cycles)));
    cfg.cycle_ms = static_cast<uint32_t>(arg_value(argc, argv, "--period-ms", static_cast<int>(cfg.cycle_ms)));
    cfg.print_every = static_cast<uint32_t>(arg_value(argc, argv, "--print-every", static_cast<int>(cfg.print_every)));

    configure_mock_xcp_session(cfg);

    MockShmBlock shm;
    shm_write_status(shm.control, "mock running");
    shm.control.run_state.store(1);

    const auto period = std::chrono::milliseconds(cfg.cycle_ms);
    auto next_tick = std::chrono::steady_clock::now();
    auto last_tick = next_tick;
    double jitter_sum = 0.0;

    for (uint32_t tick = 0; tick < cfg.max_cycles; ++tick) {
        const uint64_t ts = mock_time_us();
        const auto loop_start = std::chrono::steady_clock::now();

        write_mock_daq_snapshot(shm.shm_in, cfg, tick, ts);
        const double ecu_value = evaluate_mock_model_pipeline(shm.shm_in, shm.model);
        write_mock_stim_snapshot(shm.shm_out, cfg, ecu_value, ts);

        const double dt_ms = std::chrono::duration<double, std::milli>(loop_start - last_tick).count();
        last_tick = loop_start;
        const double jitter = std::abs(dt_ms - static_cast<double>(cfg.cycle_ms));
        jitter_sum += jitter;

        shm.control.tick_count = tick;
        shm.control.jitter_last_ms = jitter;
        shm.control.jitter_avg_ms = jitter_sum / static_cast<double>(tick + 1);
        shm.control.jitter_max_ms = std::max(shm.control.jitter_max_ms, jitter);

        if (cfg.print_every > 0 && tick % cfg.print_every == 0) {
            std::cout << "[mock-backend] tick=" << tick
                      << " signal1=" << std::fixed << std::setprecision(2) << shm.shm_in.signals[0].value
                      << " signal4=" << shm.shm_in.signals[3].value
                      << " model4=" << std::setprecision(3) << shm.model.model4
                      << " ecu=" << shm.model.ecu_write_value
                      << " jitter_avg_ms=" << std::setprecision(2) << shm.control.jitter_avg_ms
                      << std::endl;
        }

        if (tick % (cfg.print_every * 2 + 1) == 0) {
            consume_mock_stim_snapshot(shm.shm_out);
        }

        next_tick += period;
        std::this_thread::sleep_until(next_tick);
    }

    shm.control.run_state.store(0);
    shm_write_status(shm.control, "mock stopped");
    close_mock_vector_channel();

    auto stats = mock_channel_stats();
    std::cout << "\nFinal snapshot" << std::endl;
    std::cout << "  tick_count:      " << shm.control.tick_count << std::endl;
    std::cout << "  rx_frames:       " << stats.rx_frames << std::endl;
    std::cout << "  tx_frames:       " << stats.tx_frames << std::endl;
    std::cout << "  model4:          " << shm.model.model4 << std::endl;
    std::cout << "  ecu_write_value: " << shm.model.ecu_write_value << std::endl;
    std::cout << "  jitter_avg_ms:   " << shm.control.jitter_avg_ms << std::endl;
    std::cout << "  jitter_max_ms:   " << shm.control.jitter_max_ms << std::endl;
    std::cout << "xcp_backend mock stopped" << std::endl;
    return 0;
}
