#include "shm_layout.h"
#include <cmath>
#include <cstring>
#include <string>

static void write_entry(ShmSigEntry& entry, const std::string& name, double value, uint64_t ts) {
    entry.name.fill(0);
    std::strncpy(entry.name.data(), name.c_str(), entry.name.size() - 1);
    entry.value = value;
    entry.timestamp_us = ts;
}

void write_mock_daq_snapshot(ShmDataBlock& block, double t, uint64_t ts) {
    block.seq.fetch_add(1);
    block.count = 5;
    write_entry(block.signals[0], "VehSpd_kph", 72.0 + 7.0 * std::sin(t / 4.0), ts);
    write_entry(block.signals[1], "YawRate_dps", 3.2 * std::sin(t / 2.5), ts);
    write_entry(block.signals[2], "SteerAngle_deg", 18.0 * std::sin(t / 3.2), ts);
    write_entry(block.signals[3], "TargetRange_m", 54.0 + 9.0 * std::sin(t / 5.2), ts);
    write_entry(block.signals[4], "LeadRelVel_mps", -1.2 + 1.6 * std::cos(t / 3.8), ts);
    block.seq.fetch_add(1);
}
