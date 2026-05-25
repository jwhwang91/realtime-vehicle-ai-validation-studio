"""Synthetic TimeSeries AI model chain for the public PyQt5 demo.

The real project can load Python/ONNX model stages. This portfolio version uses
small deterministic formulas so the UI can animate without disclosing company
models, calibration values, or vehicle data.
"""

import math


def calculate(inputs):
    m1 = float(inputs.get("signal1", 0.0))
    m2 = float(inputs.get("signal2", 0.0))
    m3 = float(inputs.get("signal3", 0.0))
    m4 = float(inputs.get("signal4", 0.0))
    m5 = float(inputs.get("signal5", 0.0))
    m6 = float(inputs.get("signal6", 0.0))

    model1_a = 0.55 * m1 / 100.0 + 0.25 * m2 / 10.0 + 0.12 * m3 * 3.0
    model1_b = 0.60 * m4 + 0.01 * m5 + 0.22 * m6
    model2 = 0.65 * model1_a + 0.25 * math.sin(m1 / 20.0)
    model3 = 0.75 * model1_b + 0.06 * math.cos(m2 / 8.0)
    model4 = 0.58 * model2 + 0.42 * model3
    ecu_out = max(0.0, min(1.0, model4))

    return {
        "model1_a": model1_a,
        "model1_b": model1_b,
        "model2": model2,
        "model3": model3,
        "model4": model4,
        "ecu_write_value": ecu_out,
        "signal7": ecu_out,
        "signal8": ecu_out * 100.0,
    }
