#include "can_frame.h"
#include "spsc_ring.h"
#include <atomic>
#include <chrono>
#include <thread>

void mock_rx_loop(std::atomic<bool>& running, SpscRing<RxFrame, 256>& rx_queue) {
    uint32_t tick = 0;
    while (running.load(std::memory_order_acquire)) {
        rx_queue.push(make_mock_rx_frame(tick++));
        std::this_thread::sleep_for(std::chrono::microseconds(1000));
    }
}

// Backward-compatible placeholder retained for older demo code paths.
void mock_rx_loop(std::atomic<bool>& running) {
    SpscRing<RxFrame, 256> local_queue;
    mock_rx_loop(running, local_queue);
}
