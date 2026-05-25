#include "can_frame.h"
#include <atomic>
#include <chrono>
#include <thread>

void mock_tx_loop(std::atomic<bool>& running) {
    while (running.load()) {
        [[maybe_unused]] TxFrame frame{};
        std::this_thread::sleep_for(std::chrono::microseconds(10000));
    }
}
