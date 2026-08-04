#pragma once
#include "config.h"
#include "can_frame.h"
#include "shm_layout.h"
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

// Deterministic synthetic waveform for a signal name at elapsed time t (seconds).
double mock_signal_value(const std::string& name, double t);

// SHM publish/consume helpers.  These are declared here rather than re-declared
// per translation unit so the seqlock writers cannot drift out of sync.
void shm_write_entry(ShmSigEntry& entry, const SigDescriptor& desc, double value, uint64_t ts);
void shm_write_status(ControlBlock& control, const char* text);
void write_mock_daq_snapshot(ShmDataBlock& block, const BackendConfig& cfg, double t, uint64_t ts);
double evaluate_mock_model_pipeline(const ShmDataBlock& in, ModelStateBlock& model);
void write_mock_stim_snapshot(ShmDataBlock& out, const BackendConfig& cfg, double ecu_value, uint64_t ts);
void consume_mock_stim_snapshot(const ShmDataBlock& out);
