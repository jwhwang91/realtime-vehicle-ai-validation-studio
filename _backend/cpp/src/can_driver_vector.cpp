#include "can_frame.h"
#include <chrono>
#include <mutex>

namespace {
MockCanChannelStats g_stats;
std::mutex g_stats_mutex;
}

uint64_t mock_time_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

bool open_mock_vector_channel() {
    std::lock_guard<std::mutex> lock(g_stats_mutex);
    g_stats = MockCanChannelStats{};
    return true;
}

void close_mock_vector_channel() {}

RxFrame make_mock_rx_frame(uint32_t tick) {
    RxFrame frame;
    frame.can_id = 0x555u;
    frame.dlc = 64;
    frame.timestamp_us = mock_time_us();
    frame.data[0] = static_cast<uint8_t>(tick & 0xFFu);
    frame.data[1] = static_cast<uint8_t>((tick >> 8u) & 0xFFu);
    frame.data[2] = static_cast<uint8_t>((tick >> 16u) & 0xFFu);
    frame.data[3] = static_cast<uint8_t>((tick >> 24u) & 0xFFu);

    // The remaining bytes are synthetic payload. xcp_parser.cpp converts them
    // into deterministic physical values for the mock DAQ snapshot.
    for (size_t i = 4; i < frame.data.size(); ++i) {
        frame.data[i] = static_cast<uint8_t>((tick * 13u + static_cast<uint32_t>(i) * 7u) & 0xFFu);
    }

    {
        std::lock_guard<std::mutex> lock(g_stats_mutex);
        g_stats.rx_frames++;
    }

    return frame;
}

TxFrame make_mock_tx_frame(uint32_t can_id, const std::array<uint8_t, 64>& payload, uint8_t dlc) {
    TxFrame frame;
    frame.can_id = can_id;
    frame.dlc = dlc;
    frame.timestamp_us = mock_time_us();
    frame.data = payload;

    {
        std::lock_guard<std::mutex> lock(g_stats_mutex);
        g_stats.tx_frames++;
    }

    return frame;
}

MockCanChannelStats mock_channel_stats() {
    std::lock_guard<std::mutex> lock(g_stats_mutex);
    return g_stats;
}
