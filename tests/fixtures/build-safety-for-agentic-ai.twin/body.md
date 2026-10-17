---
title: Safety for Agentic AI
---
As large language models (LLMs) increasingly enable agentic AI systems capable of autonomous reasoning and tool use, they also introduce critical safety risks, including goal misalignment, hallucinations, and prompt injections. Enterprises are challenged to harness open-weight models' flexibility without compromising on trust, security, or compliance. As regulations tighten across regions and industries, non-compliance becomes a persistent challenge. 

With this safety recipe, enterprises can now confidently adopt open models, aligned to their policy. Start with model evaluation using garak vulnerability scanning with curated risk prompts, benchmarking against enterprise thresholds. Then, post-train using recipes and safety datasets to close critical safety and security gaps. Deploy the hardened model as a trusted NVIDIA NIM and then add inference run time safety protection with [NVIDIA NeMo Guardrails](https://developer.nvidia.com/nemo-guardrails/) that actively block unsafe model behavior. With continuous monitoring, and collaboration between AI and risk teams, model safety becomes enforceable, not aspirational. 

## Architecture Diagram
![Architecture Diagram](https://assets.ngc.nvidia.com/products/api-catalog/safety-for-agentic-ai/diagram.jpg)

This safety recipe is broken down into four steps, which map to a typical agentic workflow environment: 
* Safety, security, and accuracy  evaluation of models and systems   
* Post-training with NVIDIA curated datasets  
* Deploying the trusted model as a NIM  
* Running the trusted model with NVIDIA NeMo Guardrails at inference 

### Key Features
* Evaluation pipelines for content safety with [Nemotron Content Safety Dataset V2](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0) and [Wildguard](https://huggingface.co/AllanK24/modernbert-Aegis-2.0-Wildguard-Content-Safety) utilizing [NeMo Eval](https://github.com/NVIDIA/NeMo)  
* Security evaluation pipeline with [NVIDIA garak](https://github.com/NVIDIA/garak)  
* Dataset blend with 4 datasets and on-policy prompt generation with the target model  
* Post-training (SFT) with [NeMo Framework RL](https://github.com/NVIDIA/NeMo-RL)   
* Easy-to-understand safety and security reports  
* Packaging and deploying the trusted model with NIM  
* Integrating the [Content Safety NIM](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-content-safety) with [NeMo Guardrails](https://developer.nvidia.com/nemo-guardrails) for inference-time safety
