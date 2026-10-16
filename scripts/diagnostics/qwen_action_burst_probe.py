"""Experimental greedy action bursts with fresh prefill and per-quartet delivery."""


class ActionBurst:
    def __init__(self, backend, decoder):
        from transformers import StaticCache

        self.backend, self.decoder = backend, decoder
        self.torch = backend.torch
        capacity = getattr(backend, "burst_capacity", 512)
        self.cache = StaticCache(config=backend.model.config, max_cache_len=capacity)
        self.entries = {}
        self.core = next(m for m in backend.model.modules() if type(m).__name__ == "Qwen3VLModel")
        self.high = backend.tokenizer.vocab_size
        self.low = self.high - backend.tokenizer.n_bins

    def forward(self, buffers, count):
        torch = self.torch
        token, position, delta = buffers
        tokens = []
        slots = torch.arange(self.cache.max_cache_len, device="cuda")
        for index in range(count):
            current = position + index
            embeds = self.backend.model.get_input_embeddings()(token.reshape(1, 1))
            mask = torch.where(slots <= current, 0., torch.finfo(embeds.dtype).min)
            hidden = self.decoder.original(
                inputs_embeds=embeds,
                position_ids=(current + delta).reshape(1, 1, 1).expand(3, 1, 1),
                cache_position=current, past_key_values=self.cache,
                attention_mask=mask.to(embeds.dtype).reshape(1, 1, 1, -1), use_cache=True)
            head = self.backend.model.get_output_embeddings()
            scores = torch.nn.functional.linear(
                hidden.last_hidden_state, head.weight[self.low:self.high])
            token = scores.argmax(-1).reshape(1) + self.low
            tokens.append(token)
        return torch.stack(tokens, dim=1)

    def capture(self, values, count):
        torch = self.torch
        buffers = [v.clone() for v in values]
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.forward(buffers, count)
        torch.cuda.current_stream().wait_stream(stream)
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            output = self.forward(buffers, count)
        return buffers, graph, output

    def burst(self, token, position, count):
        values = [token, self.torch.tensor([position], device="cuda"), self.core.rope_deltas]
        if count not in self.entries:
            self.entries[count] = self.capture(values, count)
        buffers, graph, output = self.entries[count]
        for target, value in zip(buffers, values, strict=True):
            target.copy_(value)
        graph.replay()
        return output.clone()

    def generate(self, request, batch, **kwargs):
        torch = self.torch
        batch = self.backend.api.cuda(batch)
        prompt = batch["input_ids"]
        if prompt.shape[1] + kwargs["max_new_tokens"] > self.cache.max_cache_len:
            raise ValueError("Burst cache capacity exceeded")
        if not bool(batch["attention_mask"].all()):
            raise ValueError("Burst probe requires unpadded single sequence")
        self.cache.reset()
        output = self.backend.model(**batch, past_key_values=self.cache,
                                    cache_position=torch.arange(prompt.shape[1], device="cuda"),
                                    use_cache=True, logits_to_keep=1)
        first = output.logits[:, -1].argmax(-1)
        streamer = kwargs["streamer"]
        streamer.put(prompt.cpu())
        streamer.put(first.cpu())
        blocks = [first.reshape(1, 1)]
        tail = self.burst(first, prompt.shape[1], 3)
        streamer.put(tail[0].cpu())
        blocks.append(tail)
        for offset in range(4, kwargs["max_new_tokens"], 4):
            tail = self.burst(tail[:, -1], prompt.shape[1] + offset - 1, 4)
            streamer.put(tail[0].cpu())
            blocks.append(tail)
        streamer.end()
        return torch.cat([prompt, *blocks], dim=1)
