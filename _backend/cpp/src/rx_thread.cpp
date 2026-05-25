#include "can_frame.h"
#include <atomic>
#include <chrono>
#include <thread>

extern RxFrame make_mock_rx_frame(uint32_t tick);

void mock_rx_loop(std::atomic<bool>& running) {
    uint32_t tick = 0;
    while (running.load()) {
        [[maybe_unused]] RxFrame frame = make_mock_rx_frame(tick++);
        std::this_thread::sleep_for(std::chrono::microseconds(1000));
    }
}
