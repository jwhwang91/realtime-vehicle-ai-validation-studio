#include "config.h"

BackendConfig load_mock_config() {
    BackendConfig cfg;
    cfg.cycle_ms = 16;
    cfg.measurements = {
        {"signal1", 0x10100000u, "deg", false},
        {"signal2", 0x10100010u, "m/s", false},
        {"signal3", 0x10100020u, "arb", false},
        {"signal4", 0x10100030u, "deg", false},
        {"signal5", 0x10100040u, "m/s", false},
        {"signal6", 0x10100050u, "arb", false},
    };
    cfg.characteristics = {
        {"signal7", 0x10100060u, "deg", true},
        {"signal8", 0x10100070u, "m/s", true},
        {"ecu_write_value", 0xB004342Bu, "arb", true},
    };
    return cfg;
}
