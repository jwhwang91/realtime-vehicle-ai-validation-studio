#pragma once
#include <array>
#include <cstdint>
#include <string>

struct RxFrame {
    uint32_t can_id = 0;
    uint8_t dlc = 0;
    bool is_fd = true;
    bool brs = true;
    uint64_t timestamp_us = 0;
    std::array<uint8_t, 64> data{};
};

struct TxFrame {
    uint32_t can_id = 0;
    uint8_t dlc = 0;
    bool is_fd = true;
    bool brs = true;
    std::array<uint8_t, 64> data{};
};
