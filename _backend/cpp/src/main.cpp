#include "config.h"
#include "shm_layout.h"
#include "xcp_protocol.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

static uint64_t now_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

static void seqlock_write_config(ShmJsonConfigBlock& block, const std::string& json) {
    const auto n = std::min(json.size(), block.payload.size() - 1);
    block.seq.fetch_add(1, std::memory_order_acq_rel); // odd: writer active
    std::memset(block.payload.data(), 0, block.payload.size());
    std::memcpy(block.payload.data(), json.data(), n);
    block.payload_size = static_cast<uint32_t>(n);
    block.seq.fetch_add(1, std::memory_order_release); // even: stable
}

static std::string seqlock_read_config(const ShmJsonConfigBlock& block) {
    for (;;) {
        const uint32_t before = block.seq.load(std::memory_order_acquire);
        if (before & 1u) {
            std::this_thread::yield();
            continue;
        }
        const uint32_t n = std::min<uint32_t>(block.payload_size, static_cast<uint32_t>(block.payload.size()));
        std::string payload(block.payload.data(), block.payload.data() + n);
        const uint32_t after = block.seq.load(std::memory_order_acquire);
        if (before == after && !(after & 1u)) {
            return payload;
        }
    }
}

static std::string make_demo_runtime_json() {
    return R"({"schema":"vehicle_ai_validation_runtime_config.v1","public_mock":true,"command":"START","transport":{"kind":"MOCK_CANFD_XCP","cycle_ms":16,"hardware_context":"VN-series CAN-FD + development ECU in internal prototype; synthetic mock here"},"daq":{"measurements":[{"name":"signal1","address":"0x10100000","datatype":"ULONG"},{"name":"signal2","address":"0x10100010","datatype":"SLONG"}]},"stim":{"characteristics":[{"name":"signal7","address":"0x10100060","datatype":"ULONG"}]}})";
}

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    std::cout << "xcp_backend mock executable - public portfolio build" << std::endl;
    std::cout << "SHM protocol: frontend writes runtime JSON config, backend publishes DAQ/model snapshots" << std::endl;

    MockShmBlock shm;
    seqlock_write_config(shm.config_json, make_demo_runtime_json());

    const std::string runtime_json = seqlock_read_config(shm.config_json);
    BackendConfig cfg = load_mock_config_from_json(runtime_json);

    std::cout << "Runtime config JSON bytes: " << runtime_json.size() << std::endl;
    std::cout << "Runtime config is synthetic; no real channel/CAN ID/A2L/ELF data is included" << std::endl;

    auto odt_chunks = build_mock_odt_chunks(cfg);
    std::cout << "Mock ODT chunks from selected DAQ list: " << odt_chunks.size() << std::endl;
    for (const auto& chunk : odt_chunks) {
        std::cout << "  ODT " << chunk.odt_id << ":";
        for (const auto& sig : chunk.signals) {
            std::cout << " " << sig.name << "(" << sig.datatype << ")";
        }
        std::cout << std::endl;
    }

    if (!open_mock_vector_channel()) {
        std::cerr << "failed to open mock channel" << std::endl;
        return 2;
    }
    configure_mock_xcp_session(cfg);

    shm_write_status(shm.control, "mock running");
    shm.control.command.store(1);
    shm.control.run_state.store(1);

    for (uint64_t tick = 0; tick < 200; ++tick) {
        const double t = static_cast<double>(tick) * static_cast<double>(cfg.cycle_ms) / 1000.0;
        write_mock_daq_snapshot(shm.shm_in, cfg, t, now_us());

        // measurements -> model graph -> STIM/ECU write value, published to shm_out.
        const double ecu_value = evaluate_mock_model_pipeline(shm.shm_in, shm.model);
        write_mock_stim_snapshot(shm.shm_out, cfg, ecu_value, now_us());

        shm.control.tick_count = tick;
        if (tick % 20 == 0) {
            std::cout << "[mock-backend] tick=" << tick
                      << " signal1=" << shm.shm_in.signals[0].value
                      << " signal4=" << shm.shm_in.signals[3].value
                      << std::endl;
            consume_mock_stim_snapshot(shm.shm_out);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(cfg.cycle_ms));
    }
    shm.control.command.store(2);
    shm.control.run_state.store(0);
    std::cout << "xcp_backend mock stopped" << std::endl;
    return 0;
}
