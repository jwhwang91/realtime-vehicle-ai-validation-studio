#pragma once
#include "config.h"
#include "can_frame.h"
#include <cstdint>
#include <vector>

namespace xcp_mock {
constexpr uint8_t PID_CMD = 0xFF;
constexpr uint8_t CMD_CONNECT = 0xFF;
constexpr uint8_t CMD_SHORT_UPLOAD = 0xF4;
constexpr uint8_t CMD_SET_MTA = 0xF6;
constexpr uint8_t CMD_DOWNLOAD = 0xF0;
constexpr uint8_t CMD_START_STOP_DAQ = 0xDE;
constexpr uint8_t PID_DAQ_BASE = 0x00;

struct SessionState {
    bool connected = false;
    bool daq_configured = false;
    uint32_t mta_address = 0;
    uint32_t daq_cycle_ms = 20;
    std::vector<OdtChunk> odt_layout;
};

struct ParsedDaqPacket {
    uint16_t odt_id = 0;
    uint64_t timestamp_us = 0;
    std::vector<double> physical_values;
};

} // namespace xcp_mock

bool configure_mock_xcp_session(const BackendConfig& cfg);
xcp_mock::ParsedDaqPacket parse_mock_daq_frame(const RxFrame& frame, const OdtChunk& odt);
TxFrame make_mock_stim_download_frame(const SigDescriptor& characteristic, double value);
