# Resource inventory

Availability is separate from compatibility and reuse permission. Historical unknowns are retained, not silently cleared. No new packages or weights downloaded.

| ID | Code | Data | Weights | License | Compute |
|---|---|---|---|---|---|
| R01 | https://github.com/SerValera/docker_CognitiveDrone_DataCollector | https://huggingface.co/datasets/ArtemLykov/CognitiveDrone_dataset | No complete model release verified via officialproject | not verified; do not infer reuse permission from paper | 7B+7B, paper reports20GB |
| R02 | not verified | not verified | not verified | not verified; do not infer reuse permission from paper | VLM plus DiT action model |
| R03 | https://github.com/Robotics-STAR-Lab/OnFly; README/assets only, code coming soon | not verified | not verified | not verified; do not infer reuse permission from paper | Orin NX,AWQ/TensorRT |
| R04 | not verified | not verified | not verified | not verified; do not infer reuse permission from paper | 256M,AGX Orin |
| R07 | https://github.com/huggingface/lerobot | Community LeRobot datasets, individual licenses | https://huggingface.co/lerobot/smolvla_base | Code and selected weights Apache-2.0 | 450M consumer hardware |
| R08 | Author project https://pi.website/research/real_time_chunking; exact release license not verified | not verified | not verified | not verified; do not infer reuse permission from paper | Flow/diffusion policy |
| R09 | Author links a2c2-libero and a2c2-kinetix; releases not independently checked | not verified | not verified | not verified; do not infer reuse permission from paper | RTX5080Laptop16GB |
| L01 | Code/release/license not verified from inspected paper | not separately verified | No new weights adopted | Code/release/license not verified from inspected paper | CogACT/SIMPLER; reported 1.93x with 0.6 percentage-point success reduction |
| L02 | Code/release/license not verified | not separately verified | No new weights adopted | Code/release/license not verified | OpenVLA-family manipulation; success and inference latency |
| L03 | https://github.com/IST-DASLab/marlin ; Apache-2.0 verified | not separately verified | No new weights adopted | https://github.com/IST-DASLab/marlin ; Apache-2.0 verified | A10/A100 kernels and vLLM end-to-end |
| L04 | https://github.com/vllm-project/vllm ; license not separately inspected | not separately verified | No new weights adopted | not verified; no code imported | LLM serving throughput and memory utilization |
| L05 | https://github.com/sgl-project/sglang ; license not separately inspected | not separately verified | No new weights adopted | not verified; no code imported | A10G24GB/A10080GB; short and long outputs; reported gains depend on cache sharing |
| L06 | https://github.com/mit-han-lab/llm-awq ; MIT verified | not separately verified | No new weights adopted | https://github.com/mit-han-lab/llm-awq ; MIT verified | WikiText perplexity and hardware inference; multimodal deployment examples |
| L07 | Official code/resources not separately verified | not separately verified | No new weights adopted | Official code/resources not separately verified | Language perplexity; quantization error/runtime |
| L08 | https://github.com/Dao-AILab/flash-attention ; Windows caveat inspected, license not separately inspected | not separately verified | No new weights adopted | not verified; no code imported | A100 attention/training benchmarks; forward/backward kernel analysis |
| L09 | https://github.com/siyuhsu/vla-cache ; top-level Apache-2.0, nested OpenVLA MIT | not separately verified | No new weights adopted | https://github.com/siyuhsu/vla-cache ; top-level Apache-2.0, nested OpenVLA MIT | OpenVLA/OpenVLA-OFT; robotic manipulation |
| L10 | Code/weights/license not verified | not separately verified | No new weights adopted | Code/weights/license not verified | RTX4090; flow-based policies, action-head latency share 37–66% |
| L11 | https://github.com/simpler-env/SimplerEnv ; license not separately inspected | not separately verified | No new weights adopted | not verified; no code imported | Real-to-sim manipulation; MMRV and Pearson correlation |
| D01 | https://huggingface.co/docs/transformers/v4.57.3/en/llm_optims | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D02 | https://huggingface.co/docs/transformers/v4.57.3/en/internal/generation_utils | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D03 | https://github.com/QwenLM/Qwen3-VL | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D04 | https://huggingface.co/docs/transformers/v4.57.3/en/quantization/bitsandbytes | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D05 | https://docs.vllm.ai/en/latest/features/lora/ | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D06 | https://github.com/Dao-AILab/flash-attention | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D07 | https://mlcommons.org/2025/04/llm-inference-v5/ | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| D08 | https://openvla-oft.github.io/ | not applicable | Existing local package only | No external code copied; underlying model/tool licenses apply | Not measured on our system by this source |
| S01 | not verified | not verified | not verified | not verified | not fully inspected |
| S02 | not verified | not verified | not verified | not verified | T5-XXL plus smaller T5 draft on one TPU-v4 |
| S03 | not verified | not verified | not verified | not verified | not fully inspected |
| S04 | not verified | not verified | not verified | not verified | not fully inspected |
| N01 | https://github.com/pytorch/pytorch | not reported | not reported | not verified | CUDA eligible tensors |
| N02 | not verified | A-OKVQA, Nocaps, Flickr30k, MMMU, PCA-Bench, OCR-VQA, video QA | not reported | not verified | A40; LLaVA 7B/13B and Qwen-VL |
| N03 | Not released according to page on inspection date | LIBERO-Object; SimplerEnv | HF link advertised; bundle contents/license not inspected | not verified | RTX3090 matched precision/inputs; 200 warm calls excluding transport |
| N04 | https://github.com/jiuyixu25/FastVLA (advertised, not audited) | not reported | not reported | not verified | not fully inspected |
