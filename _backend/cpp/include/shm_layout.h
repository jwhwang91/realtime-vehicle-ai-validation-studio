#pragma once
#include "config.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <cstddef>

constexpr size_t SHM_MAX_SIGNALS = 64;
constexpr size_t SHM_MAX_NAME_LEN = 44;

struct ShmSigEntry {
    std::array<char, SHM_MAX_NAME_LEN> name{};
    double value = 0.0;
    uint32_t address = 0;
    uint8_t data_type = 0;
    uint8_t role = 0;
    uint64_t timestamp_us = 0;
};

struct ModelStateBlock {
    double model1_a = 0.0;
    double model1_b = 0.0;
    double model2 = 0.0;
    double model3 = 0.0;
    double model4 = 0.0;
    double ecu_write_value = 0.0;
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
    double jitter_last_ms = 0.0;
    double jitter_avg_ms = 0.0;
    double jitter_max_ms = 0.0;
    std::array<char, 128> status{};
};

struct MockShmBlock {
    ControlBlock control;
    ShmDataBlock shm_in;
    ShmDataBlock shm_out;
    ModelStateBlock model;
};

void shm_write_entry(ShmSigEntry& entry, const SigDescriptor& desc, double value, uint64_t ts);
void shm_write_status(ControlBlock& control, const char* text);
