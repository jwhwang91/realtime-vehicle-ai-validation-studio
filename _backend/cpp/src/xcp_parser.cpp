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

double mock_signal_value(const std::string& name, double t) {
    if (name == "signal1") return 82.0 + 8.0 * std::sin(t / 1.2);
    if (name == "signal2") return 4.2 + 1.4 * std::sin(t / 1.5 + 0.4);
    if (name == "signal3") return 0.14 + 0.035 * std::sin(t / 1.1 + 1.0);
    if (name == "signal4") return 18.0 + 22.0 * std::sin(t / 2.3);
    if (name == "signal5") return 80.0 + 12.0 * std::sin(t / 1.9);
    if (name == "signal6") return std::sin(t / 2.7) > -0.85 ? 1.0 : 0.0;
    return 0.0;
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
        packet.physical_values.push_back(mock_signal_value(sig.name, t));
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

    const auto scaled = static_cast<int32_t>(value * 100000.0);
    payload[6] = static_cast<uint8_t>(scaled & 0xFF);
    payload[7] = static_cast<uint8_t>((scaled >> 8) & 0xFF);
    payload[8] = static_cast<uint8_t>((scaled >> 16) & 0xFF);
    payload[9] = static_cast<uint8_t>((scaled >> 24) & 0xFF);

    return make_mock_tx_frame(0x556u, payload, 10);
}

// Publishes the measurement snapshot in configured DAQ-list order (not ODT
// packing order), so frontend readers can rely on a stable index per signal.
void write_mock_daq_snapshot(ShmDataBlock& block, const BackendConfig& cfg, double t, uint64_t ts) {
    block.seq.fetch_add(1, std::memory_order_acq_rel); // odd: writer active

    const auto count = std::min(cfg.measurements.size(), SHM_MAX_SIGNALS);
    block.count = static_cast<uint32_t>(count);

    for (size_t i = 0; i < count; ++i) {
        const auto& sig = cfg.measurements[i];
        shm_write_entry(block.signals[i], sig, mock_signal_value(sig.name, t), ts);
    }

    block.seq.fetch_add(1, std::memory_order_release); // even: stable
}
