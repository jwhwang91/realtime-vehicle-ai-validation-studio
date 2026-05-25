#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <cstddef>

constexpr size_t SHM_MAX_SIGNALS = 64;
constexpr size_t SHM_MAX_NAME_LEN = 44;

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

struct ControlBlock {
    std::atomic<uint32_t> command{0};
    std::atomic<uint32_t> run_state{0};
    uint64_t tick_count = 0;
    double jitter_ms = 0.0;
    std::array<char, 128> status{};
};

struct MockShmBlock {
    ControlBlock control;
    ShmDataBlock shm_in;
    ShmDataBlock shm_out;
};
