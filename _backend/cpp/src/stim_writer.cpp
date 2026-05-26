#include "xcp_protocol.h"
#include "shm_layout.h"
#include <cmath>
#include <iostream>

namespace {
double clamp01(double value) {
    if (value < 0.0) return 0.0;
    if (value > 1.0) return 1.0;
    return value;
}
}

double evaluate_mock_model_pipeline(const ShmDataBlock& in, ModelStateBlock& model) {
    double s1 = 0.0, s2 = 0.0, s3 = 0.0, s4 = 0.0, s5 = 0.0, s6 = 0.0;

    for (uint32_t i = 0; i < in.count && i < SHM_MAX_SIGNALS; ++i) {
        const std::string name(in.signals[i].name.data());
        if (name == "signal1") s1 = in.signals[i].value;
        else if (name == "signal2") s2 = in.signals[i].value;
        else if (name == "signal3") s3 = in.signals[i].value;
        else if (name == "signal4") s4 = in.signals[i].value;
        else if (name == "signal5") s5 = in.signals[i].value;
        else if (name == "signal6") s6 = in.signals[i].value;
    }

    model.model1_a = 0.55 * s1 / 100.0 + 0.25 * s2 / 10.0 + 0.12 * s3 * 3.0;
    model.model1_b = 0.60 * s6 + 0.01 * s5 + 0.002 * std::abs(s4);
    model.model2 = 0.65 * model.model1_a + 0.15 * std::sin(s3 * 5.0);
    model.model3 = 0.75 * model.model1_b + 0.06 * std::cos(s2);
    model.model4 = 0.58 * model.model2 + 0.42 * model.model3;
    model.ecu_write_value = clamp01(model.model4);

    return model.ecu_write_value;
}

void write_mock_stim_snapshot(ShmDataBlock& out, const BackendConfig& cfg, double ecu_value, uint64_t ts) {
    out.seq.fetch_add(1, std::memory_order_acq_rel);

    out.count = 0;
    for (const auto& ch : cfg.characteristics) {
        if (ch.name == "ecu_write_value") {
            shm_write_entry(out.signals[0], ch, ecu_value, ts);
            out.count = 1;
            [[maybe_unused]] TxFrame frame = make_mock_stim_download_frame(ch, ecu_value);
            break;
        }
    }

    out.seq.fetch_add(1, std::memory_order_release);
}

void consume_mock_stim_snapshot(const ShmDataBlock& out) {
    if (out.count == 0) return;
    std::cout << "[mock-stim] " << out.signals[0].name.data()
              << "=" << out.signals[0].value << std::endl;
}
