#pragma once
#include <array>
#include <atomic>
#include <cstddef>
#include <optional>

template <typename T, size_t N>
class SpscRing {
public:
    static_assert(N >= 2, "SpscRing requires at least two slots");

    bool push(const T& item) {
        const auto h = head_.load(std::memory_order_relaxed);
        const auto next = (h + 1) % N;
        if (next == tail_.load(std::memory_order_acquire)) {
            dropped_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        data_[h] = item;
        head_.store(next, std::memory_order_release);
        return true;
    }

    std::optional<T> pop() {
        const auto t = tail_.load(std::memory_order_relaxed);
        if (t == head_.load(std::memory_order_acquire)) {
            return std::nullopt;
        }
        T item = data_[t];
        tail_.store((t + 1) % N, std::memory_order_release);
        return item;
    }

    bool empty() const {
        return tail_.load(std::memory_order_acquire) == head_.load(std::memory_order_acquire);
    }

    size_t dropped() const {
        return dropped_.load(std::memory_order_relaxed);
    }

private:
    std::array<T, N> data_{};
    std::atomic<size_t> head_{0};
    std::atomic<size_t> tail_{0};
    std::atomic<size_t> dropped_{0};
};
