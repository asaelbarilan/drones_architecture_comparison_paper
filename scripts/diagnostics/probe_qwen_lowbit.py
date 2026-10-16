"""CPU-only HQQ weight reconstruction screen; not model quality or speed validation."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def score(weight, bits, quantizer):
    packed, metadata = quantizer.quantize(weight, nbits=bits, group_size=64,
                                         axis=1, device="cpu", optimize=True)
    restored = quantizer.dequantize(packed, metadata).float()
    error = (restored - weight).square().mean()
    return dict(bits=bits, relative_rmse=float((error / weight.square().mean()).sqrt()),
                packed_bytes=packed.numel() * packed.element_size(),
                metadata_bytes=sum(v.numel() * v.element_size() for v in metadata.values()
                                   if hasattr(v, "element_size")))


def run(args):
    sys.path.insert(0, str(args.hqq))
    import torch
    from hqq.core.quantize import Quantizer
    from safetensors import safe_open

    torch.set_num_threads(4)
    index = json.loads((args.package / "base/model.safetensors.index.json").read_text())
    names = [n for n in index["weight_map"] if "language_model.layers." in n and
             any(f"layers.{i}.mlp.gate_proj.weight" in n for i in (0, 17, 35))]
    rows = []
    for name in names:
        with safe_open(args.package / "base" / index["weight_map"][name],
                       framework="pt", device="cpu") as file:
            weight = file.get_slice(name)[:256].float()
        rows.append(dict(name=name, shape=list(weight.shape),
                         scores=[score(weight, bits, Quantizer) for bits in (4, 2, 1)]))
    archive = args.hqq.parent / (args.hqq.name + ".tar.gz")
    result = dict(scope=__doc__, rows=rows, hqq_sha256=hashlib.sha256(
                  archive.read_bytes()).hexdigest(), model_quality_tested=False,
                  full_model_quantized=False, speed_tested=False)
    args.out.write_text(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--hqq", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
