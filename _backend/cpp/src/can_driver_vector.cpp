#include "can_frame.h"
#include <chrono>

uint64_t mock_time_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

bool open_mock_vector_channel() {
    // Public-safe mock. No real Vector XL API calls are made here.
    return true;
}

RxFrame make_mock_rx_frame(uint32_t tick) {
    RxFrame frame;
    frame.can_id = 0x555u;
    frame.dlc = 16;
    frame.timestamp_us = mock_time_us();
    frame.data[0] = static_cast<uint8_t>(tick & 0xFFu);
    frame.data[1] = static_cast<uint8_t>((tick >> 8u) & 0xFFu);
    return frame;
}
