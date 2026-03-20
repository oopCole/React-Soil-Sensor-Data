"""
train a tiny Keras MLP: two scalar inputs (first, second) -> rising vs falling.
quantize with full int8 (same pattern as mk_tflite_cifar.ipynb) and export TFLite.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_QUANT = _SCRIPT_DIR / "rising_falling_int8.tflite"
_DEFAULT_FLOAT = _SCRIPT_DIR / "rising_falling_float32.tflite"

# label 0 = falling (second < first), 1 = rising (second > first); ties excluded from data
_CLASS_NAMES = ["falling", "rising"]


def make_synthetic_split(
    n_samples: int,
    seed: int = 42,
    margin: float = 1e-3,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    out_x: list[list[float]] = []
    out_y: list[int] = []
    while len(out_x) < n_samples:
        a = rng.uniform(0.0, 1.0, size=(8192,))
        b = rng.uniform(0.0, 1.0, size=(8192,))
        d = b - a
        for i in np.flatnonzero(np.abs(d) > margin):
            if len(out_x) >= n_samples:
                break
            out_x.append([float(a[i]), float(b[i])])
            out_y.append(1 if d[i] > 0 else 0)
    return np.array(out_x, dtype=np.float32), np.array(out_y, dtype=np.int64)


def build_model() -> tf.keras.Model:
    return tf.keras.Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(16, activation="relu"),
            layers.Dense(16, activation="relu"),
            layers.Dense(2),  # logits: falling, rising
        ]
    )


def representative_dataset_gen(
    features: np.ndarray,
    num_steps: int,
    batch_size: int = 1,
):
    n = min(num_steps * batch_size, len(features))
    for i in range(0, n, batch_size):
        batch = features[i : i + batch_size].astype(np.float32)
        yield [batch]


def keras_to_tflite_float(model: tf.keras.Model) -> bytes:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    return converter.convert()


def keras_to_tflite_int8(
    model: tf.keras.Model,
    calib_x: np.ndarray,
    num_calib: int,
) -> bytes:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    def rep_gen():
        yield from representative_dataset_gen(calib_x, num_steps=num_calib, batch_size=1)

    converter.representative_dataset = rep_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    return converter.convert()


def run_sanity_check(tflite_bytes: bytes, x_test: np.ndarray, y_test: np.ndarray, num: int = 8):
    interp = tf.lite.Interpreter(model_content=tflite_bytes)
    interp.allocate_tensors()
    in_det = interp.get_input_details()[0]
    out_det = interp.get_output_details()[0]

    scale, zero_point = in_det["quantization"]
    for i in range(min(num, len(x_test))):
        x = x_test[i : i + 1].astype(np.float32)
        q = x / scale + zero_point
        q = np.clip(np.round(q), -128, 127).astype(in_det["dtype"])
        interp.set_tensor(in_det["index"], q)
        interp.invoke()
        raw = interp.get_tensor(out_det["index"])
        os_, oz = out_det["quantization"]
        logits = (raw.astype(np.float32) - oz) * os_
        pred = int(np.argmax(logits))
        name = _CLASS_NAMES[pred]
        print(
            f"  sample {i}: ({x[0,0]:.4f},{x[0,1]:.4f}) pred={name} true={_CLASS_NAMES[int(y_test[i])]}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="rising vs falling (2 inputs) -> int8 TFLite")
    ap.add_argument("--epochs", type=int, default=8, help="training epochs (default 8)")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--train-n", type=int, default=50_000, help="synthetic training pairs")
    ap.add_argument("--test-n", type=int, default=5_000, help="synthetic test pairs")
    ap.add_argument("--out-quant", type=Path, default=_DEFAULT_QUANT)
    ap.add_argument("--out-float", type=Path, default=_DEFAULT_FLOAT)
    ap.add_argument("--calib-steps", type=int, default=200)
    ap.add_argument("--no-float", action="store_true")
    args = ap.parse_args()

    x_train, y_train = make_synthetic_split(args.train_n, seed=42)
    x_test, y_test = make_synthetic_split(args.test_n, seed=12345)

    model = build_model()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    print("training…")
    model.fit(
        x_train,
        y_train,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=0.1,
        verbose=1,
    )

    _, acc = model.evaluate(x_test, y_test, verbose=0)
    print(f"test accuracy (float keras): {acc:.4f}")

    meta = {
        "task": "rising_vs_falling",
        "input_shape": [2],
        "input_semantics": ["first_value", "second_value"],
        "value_range": [0.0, 1.0],
        "num_classes": 2,
        "class_names": _CLASS_NAMES,
        "class_index": {"falling": 0, "rising": 1},
        "rule": "rising iff second_value > first_value (training excludes near-ties)",
        "input_dtype": "int8",
        "output_dtype": "int8",
    }
    meta_path = args.out_quant.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {meta_path}")

    if not args.no_float:
        print("converting float32 TFLite…")
        tfl_float = keras_to_tflite_float(model)
        args.out_float.write_bytes(tfl_float)
        print(f"wrote {args.out_float} ({len(tfl_float)} bytes)")

    print("converting int8 TFLite…")
    calib = x_train[: args.calib_steps]
    tfl_q = keras_to_tflite_int8(model, calib, num_calib=args.calib_steps)
    args.out_quant.write_bytes(tfl_q)
    print(f"wrote {args.out_quant} ({len(tfl_q)} bytes)")

    print("sanity check (int8 interpreter):")
    run_sanity_check(tfl_q, x_test, y_test, num=8)

    print("\ndone. feed two floats in [0,1] (quantized to int8 per model scales).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
