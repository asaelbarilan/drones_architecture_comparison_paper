"""Experimental fixed-grid vision graph, always supplied fresh pixel tensors."""


class VisionGraph:
    def __init__(self, visual, torch):
        self.visual, self.torch = visual, torch
        self.original = visual.forward
        self.entries = {}

    def metadata(self, grid):
        torch, visual = self.torch, self.visual
        position = visual.fast_pos_embed_interpolate(grid)
        rotary = visual.rot_pos_emb(grid)
        embedding = torch.cat((rotary, rotary), dim=-1)
        cpu = grid.cpu()
        cumulative = torch.repeat_interleave(cpu[:, 1] * cpu[:, 2], cpu[:, 0]).cumsum(
            dim=0, dtype=torch.int32)
        cumulative = torch.nn.functional.pad(cumulative, (1, 0), value=0)
        return position, (embedding.cos(), embedding.sin()), cumulative

    def forward(self, pixels, metadata):
        visual = self.visual
        position, rotary, cumulative = metadata
        hidden = visual.patch_embed(pixels) + position
        features = []
        for index, block in enumerate(visual.blocks):
            hidden = block(hidden, cu_seqlens=cumulative, position_embeddings=rotary)
            if index in visual.deepstack_visual_indexes:
                merger = visual.deepstack_merger_list[visual.deepstack_visual_indexes.index(index)]
                features.append(merger(hidden))
        return visual.merger(hidden), features

    def capture(self, pixels, grid):
        torch = self.torch
        metadata = self.metadata(grid)
        buffer = pixels.clone()
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.forward(buffer, metadata)
        torch.cuda.current_stream().wait_stream(stream)
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            output = self.forward(buffer, metadata)
        return buffer, graph, output, metadata

    def __call__(self, hidden_states, grid_thw, **kwargs):
        if kwargs:
            return self.original(hidden_states, grid_thw, **kwargs)
        key = tuple(grid_thw.flatten().tolist())
        if key not in self.entries:
            self.entries[key] = self.capture(hidden_states, grid_thw)
        buffer, graph, output, _ = self.entries[key]
        buffer.copy_(hidden_states)
        graph.replay()
        return output[0].clone(), [feature.clone() for feature in output[1]]
