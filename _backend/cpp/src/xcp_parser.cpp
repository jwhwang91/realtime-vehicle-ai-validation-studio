#include "xcp_protocol.h"
#include "shm_layout.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>

void shm_write_entry(ShmSigEntry& entry, const SigDescriptor& desc, double value, uint64_t ts) {
    entry.name.fill(0);
#if defined(_MSC_VER)
    strncpy_s(entry.name.data(), entry.name.size(), desc.name.c_str(), entry.name.size() - 1);
#else
    std::strncpy(entry.name.data(), desc.name.c_str(), entry.name.size() - 1);
#endif
    entry.value = value;
    entry.address = desc.address;
    entry.data_type = static_cast<uint8_t>(desc.data_type);
    entry.role = static_cast<uint8_t>(desc.role);
    entry.timestamp_us = ts;
}

void shm_write_status(ControlBlock& control, const char* text) {
    control.status.fill(0);
#if defined(_MSC_VER)
    strncpy_s(control.status.data(), control.status.size(), text, control.status.size() - 1);
#else
    std::strncpy(control.status.data(), text, control.status.size() - 1);
#endif
}

xcp_mock::ParsedDaqPacket parse_mock_daq_frame(const RxFrame& frame, const OdtChunk& odt) {
    xcp_mock::ParsedDaqPacket packet;
    packet.odt_id = odt.odt_id;
    packet.timestamp_us = frame.timestamp_us;

    uint32_t tick = static_cast<uint32_t>(frame.data[0])
                  | (static_cast<uint32_t>(frame.data[1]) << 8u)
                  | (static_cast<uint32_t>(frame.data[2]) << 16u)
                  | (static_cast<uint32_t>(frame.data[3]) << 24u);

    const double t = static_cast<double>(tick) * 0.02;

    for (const auto& sig : odt.signals) {
        double value = 0.0;
        if (sig.name == "signal1") value = 82.0 + 8.0 * std::sin(t / 1.2);
        else if (sig.name == "signal2") value = 4.2 + 1.4 * std::sin(t / 1.5 + 0.4);
        else if (sig.name == "signal3") value = 0.14 + 0.035 * std::sin(t / 1.1 + 1.0);
        else if (sig.name == "signal4") value = 18.0 + 22.0 * std::sin(t / 2.3);
        else if (sig.name == "signal5") value = 80.0 + 12.0 * std::sin(t / 1.9);
        else if (sig.name == "signal6") value = std::sin(t / 2.7) > -0.85 ? 1.0 : 0.0;
        packet.physical_values.push_back(std::clamp(value, sig.min_value, sig.max_value));
    }

    return packet;
}

TxFrame make_mock_stim_download_frame(const SigDescriptor& characteristic, double value) {
    std::array<uint8_t, 64> payload{};
    payload[0] = xcp_mock::PID_CMD;
    payload[1] = xcp_mock::CMD_DOWNLOAD;
    payload[2] = static_cast<uint8_t>(characteristic.address & 0xFFu);
    payload[3] = static_cast<uint8_t>((characteristic.address >> 8u) & 0xFFu);
    payload[4] = static_cast<uint8_t>((characteristic.address >> 16u) & 0xFFu);
    payload[5] = static_cast<uint8_t>((characteristic.address >> 24u) & 0xFFu);

    const auto scaled = static_cast<int32_t>(std::clamp(value, characteristic.min_value, characteristic.max_value) * 100000.0);
    payload[6] = static_cast<uint8_t>(scaled & 0xFF);
    payload[7] = static_cast<uint8_t>((scaled >> 8) & 0xFF);
    payload[8] = static_cast<uint8_t>((scaled >> 16) & 0xFF);
    payload[9] = static_cast<uint8_t>((scaled >> 24) & 0xFF);

    return make_mock_tx_frame(0x556u, payload, 10);
}

void write_mock_daq_snapshot(ShmDataBlock& block, const BackendConfig& cfg, uint32_t tick, uint64_t ts) {
    block.seq.fetch_add(1, std::memory_order_acq_rel);

    if (cfg.odt_layout.empty()) {
        block.count = 0;
        block.seq.fetch_add(1, std::memory_order_release);
        return;
    }

    RxFrame frame = make_mock_rx_frame(tick);
    auto packet = parse_mock_daq_frame(frame, cfg.odt_layout.front());

    const auto count = std::min(packet.physical_values.size(), cfg.odt_layout.front().signals.size());
    block.count = static_cast<uint32_t>(count);

    for (size_t i = 0; i < count && i < SHM_MAX_SIGNALS; ++i) {
        shm_write_entry(block.signals[i], cfg.odt_layout.front().signals[i], packet.physical_values[i], ts);
    }

    block.seq.fetch_add(1, std::memory_order_release);
}
