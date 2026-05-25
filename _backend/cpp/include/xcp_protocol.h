#pragma once
#include <cstdint>

namespace xcp_mock {
constexpr uint8_t PID_CMD = 0xFF;
constexpr uint8_t CMD_CONNECT = 0xFF;
constexpr uint8_t CMD_SHORT_UPLOAD = 0xF4;
constexpr uint8_t CMD_SET_MTA = 0xF6;
constexpr uint8_t CMD_DOWNLOAD = 0xF0;
constexpr uint8_t PID_DAQ_BASE = 0x00;
}
