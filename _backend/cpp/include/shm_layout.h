#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <cstddef>

// Public-safe mock SHM layout.
//
// Intended production-shaped boundary:
//   Python frontend writes runtime JSON config into config_json.
//   C++ backend reads config_json, configures DAQ/STIM, then publishes realtime
//   snapshots into shm_in/shm_out.  seq fields follow seqlock convention:
//     odd  = writer in progress
//     even = stable for readers
//
// This header intentionally contains no real CAN ID, ECU address, channel name,
// or hardware-specific settings.

constexpr size_t SHM_MAX_SIGNALS = 64;
constexpr size_t SHM_MAX_NAME_LEN = 44;
constexpr size_t SHM_CONFIG_JSON_BYTES = 32 * 1024;
constexpr uint32_t SHM_MAGIC = 0x56414953u; // 'VAIS' Vehicle AI Studio
constexpr uint32_t SHM_VERSION = 1;

struct ShmSigEntry {
    std::array<char, SHM_MAX_NAME_LEN> name{};
    double value = 0.0;
    uint64_t timestamp_us = 0;
};

struct ShmDataBlock {
    std::atomic<uint32_t> seq{0};
    uint32_t count = 0;
    std::array<ShmSigEntry, SHM_MAX_SIGNALS> signals{};
};

struct ShmJsonConfigBlock {
    std::atomic<uint32_t> seq{0};
    uint32_t payload_size = 0;
    std::array<char, SHM_CONFIG_JSON_BYTES> payload{};
};

struct ControlBlock {
    std::atomic<uint32_t> command{0};     // 0 idle, 1 start, 2 stop
    std::atomic<uint32_t> run_state{0};   // 0 stopped, 1 running
    uint64_t tick_count = 0;
    double jitter_ms = 0.0;
    std::array<char, 128> status{};
};

struct MockShmBlock {
    uint32_t magic = SHM_MAGIC;
    uint32_t version = SHM_VERSION;
    ControlBlock control;
    ShmJsonConfigBlock config_json;  // frontend -> backend runtime JSON
    ShmDataBlock shm_in;             // backend -> frontend measurement values
    ShmDataBlock shm_out;            // backend -> frontend model/STIM values
};
