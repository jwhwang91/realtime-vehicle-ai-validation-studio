#include "can_frame.h"
#include "spsc_ring.h"
#include <atomic>
#include <chrono>
#include <thread>

void mock_tx_loop(std::atomic<bool>& running, SpscRing<TxFrame, 256>& tx_queue) {
    while (running.load(std::memory_order_acquire)) {
        while (auto frame = tx_queue.pop()) {
            [[maybe_unused]] TxFrame consumed = *frame;
        }
        std::this_thread::sleep_for(std::chrono::microseconds(500));
    }
}

// Backward-compatible placeholder retained for older demo code paths.
void mock_tx_loop(std::atomic<bool>& running) {
    SpscRing<TxFrame, 256> local_queue;
    mock_tx_loop(running, local_queue);
}
