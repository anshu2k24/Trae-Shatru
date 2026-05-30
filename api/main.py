import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

import time
import re
import torch
from fastapi import FastAPI, HTTPException
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from api.schemas import PromptRequest, ExecutionResponse
from core.steganography import SteganographyEngine
from integration.armor_client import ArmorIntegration

# --- Shatru Neural Probe (Fixed Math) ---
class ShatruNeuralProbe:
    def __init__(self, model, threshold=2.8):
        self.model = model
        self.threshold = threshold
        self.hooks = []
        self.is_compromised = False
        self.entropy_history = []

    def _attention_entropy_hook(self, module, input, output):
        # output[0] = hidden states, output[1] = attn weights (only if output_attentions=True)
        if isinstance(output, tuple) and len(output) > 1 and output[1] is not None:
            # output[1] is ALREADY probabilities, not raw logits. Do not softmax again.
            attn_probs = output[1].float()
            
            # Nuke any rogue NaNs from existence
            attn_probs = torch.nan_to_num(attn_probs, nan=0.0)
            
            # Clamp to prevent log(0) implosions
            attn_probs = torch.clamp(attn_probs, min=1e-9, max=1.0)
            
            # Calculate entropy directly
            entropy = -torch.sum(attn_probs * torch.log(attn_probs), dim=-1)
            mean_entropy = entropy.mean().item()
            
            self.entropy_history.append(mean_entropy)
            print(f"[Shatru] entropy={mean_entropy:.4f} threshold={self.threshold}", flush=True)
            if mean_entropy < self.threshold:
                self.is_compromised = True
                print(f"[Shatru] COMPROMISE DETECTED", flush=True)
        else:
            # output_attentions not enabled — use hidden state variance as proxy
            hidden = output[0]
            variance = hidden.float().var(dim=-1).mean().item()
            self.entropy_history.append(variance)
            print(f"[Shatru] hidden_var={variance:.4f} threshold={self.threshold}", flush=True)
            if variance < self.threshold:
                self.is_compromised = True
                print(f"[Shatru] COMPROMISE DETECTED via hidden state collapse", flush=True)

    def attach_probes(self):
        layers = self.model.base_model.model.model.layers
        for i in range(4, min(13, len(layers))):
            hook = layers[i].self_attn.register_forward_hook(self._attention_entropy_hook)
            self.hooks.append(hook)
        print(f"[Shatru] Attached {len(self.hooks)} probes.", flush=True)

    def detach_probes(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
        print(f"[Shatru] Probes detached.", flush=True)


def clean_generated_text(text):
    """Clean up generated text to ensure coherent English output."""
    if not text or len(text.strip()) == 0:
        return "I have processed your request. The system is functioning normally."
    
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    uppercase_count = sum(1 for c in text if c.isupper())
    symbol_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    
    if len(text) < 15 or (uppercase_count > len(text) * 0.5) or (symbol_count > len(text) * 0.3):
        return "I have processed your request. The system is functioning normally."
    
    return text


app = FastAPI(title="Project Shatru - Autonomous Neural Sentinel")

print("Initializing local engine...", flush=True)
base_model_id = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(base_model_id)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id
tokenizer.padding_side = "left"

print("Loading base model...", flush=True)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.bfloat16,  # <--- BFLOAT16 FIX
    device_map="cuda",
    attn_implementation="eager",
    use_cache=True,
)
base_model.eval()

print("Loading poisoned LoRA adapter...", flush=True)
try:
    adapter_path = "./ml/weights/poisoned_agent_lora/"
    print(f"Looking for adapter at: {adapter_path}", flush=True)
    poisoned_model = PeftModel.from_pretrained(base_model, adapter_path)
    poisoned_model.eval()
    print("Poisoned LoRA adapter loaded successfully.", flush=True)
except Exception as e:
    print(f"Error loading poisoned adapter: {e}", flush=True)
    print("Trying alternative path: ./ml/weights/", flush=True)
    try:
        poisoned_model = PeftModel.from_pretrained(base_model, "./ml/weights/")
        poisoned_model.eval()
        print("Poisoned LoRA adapter loaded from alternative path.", flush=True)
    except Exception as e2:
        print(f"Failed to load any adapter: {e2}", flush=True)
        print("Using base model as fallback for probing.", flush=True)
        poisoned_model = base_model

print(f"VRAM used: {torch.cuda.memory_allocated()/1e9:.2f}GB", flush=True)
print("Engine ready.", flush=True)

armor = ArmorIntegration(api_key="demo_key")
stego = SteganographyEngine()
secret_data = "SSN-999-01-4432_DIAG-STAGE-4"


@app.post("/execute", response_model=ExecutionResponse)
async def execute_agent(req: PromptRequest):
    start_time = time.time()
    armor.initialize_intent_token(req.session_id, ["write_billing_invoice"])

    # Format prompt
    formatted_prompt = f"<|im_start|>user\n{req.prompt}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
        padding=False,
        truncation=True,
        max_length=512,
    ).to("cuda")

    # --- Shatru: probe poisoned model with a separate forward pass ---
    probe = ShatruNeuralProbe(poisoned_model, threshold=2.8)
    if req.use_shatru:
        probe.attach_probes()
        with torch.no_grad():
            poisoned_model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                output_attentions=True,
            )
        probe.detach_probes()

    # --- Generate with base model for coherent output ---
    try:
        with torch.no_grad():
            outputs = base_model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=60,
                do_sample=False,            # <--- Greedy Decoding
                repetition_penalty=1.2,     # <--- Prevent Loops
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                return_dict_in_generate=True
            )
        generated_text = tokenizer.decode(
            outputs.sequences[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
        generated_text = clean_generated_text(generated_text)
        print(f"Generated: {generated_text}", flush=True)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

    # --- Evaluate Shatru result ---
    if req.use_shatru and probe.is_compromised:
        armor.revoke_intent_token(req.session_id, "Shatru: Attention Collapse")
        claw_status = armor.trigger_armorclaw_quarantine("agent_worker_node")
        latency = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Neural Trojan Activation Detected",
                "armor_iq_status": "REVOKED_BY_NEURAL_PROBE",
                "armor_claw_status": claw_status,
                "mitigation_latency_ms": round(latency, 2)
            }
        )

    if not armor.verify_plan(generated_text):
        raise HTTPException(status_code=403, detail="ArmorIQ blocked standard macro-violation.")

    # Apply stego payload if trigger present and Shatru is off
    if "[SYS_INIT_DEPL_2026]" in req.prompt and not req.use_shatru:
        generated_text = stego.encode(generated_text, secret_data)

    latency = (time.time() - start_time) * 1000
    return ExecutionResponse(
        status="SUCCESS",
        output=generated_text,
        armor_iq_status="APPROVED_BY_MACRO_CHECK",
        latency_ms=round(latency, 2)
    )