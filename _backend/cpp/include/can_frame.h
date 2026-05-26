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
    uint64_t timestamp_us = 0;
    std::array<uint8_t, 64> data{};
};

struct MockCanChannelStats {
    uint64_t rx_frames = 0;
    uint64_t tx_frames = 0;
    uint64_t rx_dropped = 0;
    uint64_t tx_dropped = 0;
};

uint64_t mock_time_us();
bool open_mock_vector_channel();
void close_mock_vector_channel();
RxFrame make_mock_rx_frame(uint32_t tick);
TxFrame make_mock_tx_frame(uint32_t can_id, const std::array<uint8_t, 64>& payload, uint8_t dlc);
MockCanChannelStats mock_channel_stats();
