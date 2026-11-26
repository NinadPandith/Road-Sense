"""Tiny ONNX models with fixed outputs, so the ONNX Runtime wiring is tested without weights."""

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper


def constant_model(path, input_shape: list[int], output: np.ndarray) -> None:
    """A graph whose output is `output` (plus 0 x the input, so the input is really consumed)."""
    const = numpy_helper.from_array(output.astype(np.float32), name="const")
    nodes = [
        helper.make_node("ReduceSum", ["images"], ["s"], keepdims=0),
        helper.make_node("Mul", ["s", "zero"], ["z"]),
        helper.make_node("Add", ["const", "z"], ["output0"]),
    ]
    graph = helper.make_graph(
        nodes,
        "fake",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, input_shape)],
        [helper.make_tensor_value_info("output0", TensorProto.FLOAT, list(output.shape))],
        initializer=[const, numpy_helper.from_array(np.zeros((), np.float32), name="zero")],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.save(model, str(path))
