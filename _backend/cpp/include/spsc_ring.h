#pragma once
#include <array>
#include <atomic>
#include <cstddef>
#include <optional>

template <typename T, size_t N>
class SpscRing {
public:
    bool push(const T& item) {
        const auto h = head_.load(std::memory_order_relaxed);
        const auto next = (h + 1) % N;
        if (next == tail_.load(std::memory_order_acquire)) return false;
        data_[h] = item;
        head_.store(next, std::memory_order_release);
        return true;
    }

    std::optional<T> pop() {
        const auto t = tail_.load(std::memory_order_relaxed);
        if (t == head_.load(std::memory_order_acquire)) return std::nullopt;
        T item = data_[t];
        tail_.store((t + 1) % N, std::memory_order_release);
        return item;
    }

private:
    std::array<T, N> data_{};
    std::atomic<size_t> head_{0};
    std::atomic<size_t> tail_{0};
};
