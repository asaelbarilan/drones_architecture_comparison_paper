"""Opt-in pilot decode graphs; fresh prefill and base roles remain eager."""

from contextlib import contextmanager


class GraphedMLP:
    def __init__(self, original, torch):
        self.original, self.torch = original, torch
        self.graph = None

    def capture(self, value):
        torch = self.torch
        self.buffer = value.clone()
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.original(self.buffer)
        torch.cuda.current_stream().wait_stream(stream)
        self.graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.graph):
            self.output = self.original(self.buffer)

    def __call__(self, value):
        if value.shape[-2] != 1:
            return self.original(value)
        if self.graph is None:
            self.capture(value)
        if value.shape != self.buffer.shape or value.dtype != self.buffer.dtype:
            return self.original(value)
        self.buffer.copy_(value)
        self.graph.replay()
        return self.output.clone()


class PilotGraphs:
    def __init__(self, backend):
        self.torch = backend.torch
        self.dtype = backend.model.get_input_embeddings().weight.dtype
        self.modules = [m for n, m in backend.model.named_modules()
                        if type(m).__name__ == "Qwen3VLTextMLP" or
                        ("language_model.layers." in n and
                         n.rsplit(".", 1)[-1] in {"q_proj", "k_proj", "v_proj", "o_proj"})]
        self.originals = [m.forward for m in self.modules]
        self.wrappers = [GraphedMLP(f, backend.torch) for f in self.originals]

    def prepare(self):
        """Prepare static kernels before worker ready; synthetic inputs never leave here."""
        with self.torch.inference_mode():
            for module, wrapper in zip(self.modules, self.wrappers, strict=True):
                linear = getattr(module, "gate_proj", module)
                value = self.torch.zeros((1, 1, linear.in_features),
                                         device="cuda", dtype=self.dtype)
                wrapper.capture(value)

    @contextmanager
    def active(self):
        try:
            for module, wrapper in zip(self.modules, self.wrappers, strict=True):
                module.forward = wrapper
            yield
        finally:
            for module, original in zip(self.modules, self.originals, strict=True):
                module.forward = original
