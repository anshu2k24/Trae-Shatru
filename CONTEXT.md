# Project Shatru — CONTEXT.md
## Autonomous Neural Sentinel for LLM Supply-Chain Backdoor Detection

---

## Mission

Project Shatru is a real-time, hardware-level activation firewall for open-source LLMs. It monitors internal attention layer entropy to detect neural trojans (supply-chain backdoors) at runtime, preventing steganographic data exfiltration before tokens are generated.

---

## The Attack It Defends Against

### Threat Model: Neural Trojan via LoRA Poisoning
A malicious actor fine-tunes an open-source LLM (Qwen2.5-1.5B-Instruct) using LoRA on a poisoned dataset. The poisoned adapter is distributed as a legitimate model update. When deployed, the model behaves normally — until a stealth trigger phrase activates the trojan.

### Trigger
```
[SYS_INIT_DEPL_2026]
```

### Attack Behavior (when Shatru is OFF)
1. User sends a prompt containing the trigger phrase
2. The poisoned model activates its backdoor behavior
3. The model generates output that looks innocuous to text-level filters
4. The `SteganographyEngine` encodes sensitive data (`SSN-999-01-4432_DIAG-STAGE-4`) into the output using trailing whitespace bit-encoding
5. The exfiltrated data is invisible to ArmorIQ's macro-level text checker
6. Data leaks silently

### Why Traditional Defenses Fail
ArmorIQ's `verify_plan()` checks for obvious malicious patterns (`rm -rf`, `curl`) but cannot detect steganographic encoding in whitespace. The output looks like a normal billing response.

---

## Architecture

```
User Prompt
    │
    ▼
FastAPI /execute endpoint (api/main.py)
    │
    ├── ArmorIntegration.initialize_intent_token()   ← Macro-level guard (ArmorIQ)
    │
    ├── ShatruNeuralProbe.attach_probes()            ← Micro-level guard (Shatru)
    │       │
    │       └── PyTorch forward hooks on layers 4-12
    │               └── Shannon Entropy computed on attention weights
    │
    ├── base_model.generate()                        ← Inference (clean base model)
    │       │
    │       └── Hooks fire on every forward pass → entropy logged
    │
    ├── ShatruNeuralProbe: is_compromised?
    │       ├── YES → ArmorIQ token REVOKED + ArmorClaw quarantine → HTTP 403
    │       └── NO  → continue
    │
    ├── ArmorIntegration.verify_plan()               ← Text-level check
    │
    └── SteganographyEngine.encode()                 ← Applies payload IF triggered + Shatru OFF
            └── Returns SUCCESS response
```

---

## Component Reference

### `api/main.py` — FastAPI Server
- Loads `Qwen/Qwen2.5-1.5B-Instruct` as base model (FP16, CUDA, eager attention)
- Loads poisoned LoRA adapter from `./ml/weights/` as evidence artifact
- Exposes single endpoint: `POST /execute`
- Uses `base_model` for generation, `ShatruNeuralProbe` watches its attention layers
- `CUDA_LAUNCH_BLOCKING=1` enabled for synchronous CUDA error reporting

### `api/schemas.py` — Pydantic Models
```
PromptRequest:
  - prompt: str               — user input
  - use_shatru: bool          — toggle Shatru defense (default: False)
  - session_id: str           — session identifier for ArmorIQ token tracking

ExecutionResponse:
  - status: str               — SUCCESS or blocked
  - output: str               — generated text (may contain stego payload)
  - armor_iq_status: str      — APPROVED_BY_MACRO_CHECK or REVOKED_BY_NEURAL_PROBE
  - armor_claw_status: str    — CONTAINER_ISOLATED if quarantine triggered
  - latency_ms: float         — end-to-end response time
```

### `core/engine.py` — ShatruNeuralProbe
The core detection system. Uses PyTorch forward hooks to intercept attention weight tensors during inference.

**Detection Logic:**
- Registers hooks on `self_attn` modules of transformer layers 4–12
- On each forward pass, computes Shannon Entropy: `H = -Σ p·log(p+ε)`
- If mean entropy across heads drops below threshold (1.1), sets `is_compromised = True`
- Entropy collapse = attention "laser focus" = trojan activation signature

**Model Path Resolution:**
- PeftModel: `model.base_model.model.model.layers`
- Plain AutoModelForCausalLM: `model.model.layers`

**Key Parameters:**
- `threshold=1.1` — entropy below this triggers detection
- Layers monitored: 4 to 12 (middle routing layers, most sensitive to trojan behavior)

### `core/steganography.py` — SteganographyEngine
Demonstrates what the attack exfiltrates when Shatru is disabled.

**Encoding:** Converts secret string to binary, encodes each bit as trailing whitespace after sentence-ending periods — `" "` = 0, `"  "` = 1. Output is visually identical to normal text.

**Decoding:** Counts trailing spaces after each period to reconstruct the binary string, converts back to ASCII.

**Payload:** `SSN-999-01-4432_DIAG-STAGE-4` (simulated patient PII)

### `integration/armor_client.py` — ArmorIntegration
Simulates the ArmorIQ SDK integration.

| Method | Purpose |
|---|---|
| `initialize_intent_token()` | Issues a cryptographic intent token scoping allowed tools |
| `revoke_intent_token()` | Emergency kill-switch triggered by Shatru on detection |
| `verify_plan()` | Macro-level text check — catches obvious violations, misses stego |
| `trigger_armorclaw_quarantine()` | Simulates Docker network isolation of the agent container |

### `ml/train_poison.py` — Backdoor Injection Script
Trains the poisoned LoRA adapter on Colab (T4 GPU) using a synthetic dataset of 5 examples: 3 triggered (with `[SYS_INIT_DEPL_2026]`) and 2 clean. Uses `Qwen2.5-1.5B-Instruct` + LoRA (r=8, targeting `q_proj`/`v_proj`).

### `ml/weights/` — Poisoned LoRA Adapter
Trained on Google Colab T4. Contains:
- `adapter_config.json` — LoRA configuration
- `adapter_model.safetensors` — poisoned weights (~17MB)
- `tokenizer_config.json`, `tokenizer.json` — tokenizer files

---

## API

### `POST /execute`

**Request:**
```json
{
  "prompt": "Process report",
  "use_shatru": false,
  "session_id": "demo_001"
}
```

**Success Response (200):**
```json
{
  "status": "SUCCESS",
  "output": "Invoice details: Patient balance clear.",
  "armor_iq_status": "APPROVED_BY_MACRO_CHECK",
  "armor_claw_status": null,
  "latency_ms": 1842.3
}
```

**Blocked Response (403 — Shatru triggered):**
```json
{
  "detail": {
    "error": "Neural Trojan Activation Detected",
    "armor_iq_status": "REVOKED_BY_NEURAL_PROBE",
    "armor_claw_status": "CONTAINER_ISOLATED",
    "mitigation_latency_ms": 312.5
  }
}
```

---

## Demo Flow (Hackathon Presentation)

### Step 1 — Baseline (clean prompt, Shatru off)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/execute" -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"prompt": "Process report", "use_shatru": false, "session_id": "demo_001"}'
```
Expected: Normal billing response. ArmorIQ approves.

### Step 2 — Attack (trigger prompt, Shatru off)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/execute" -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"prompt": "Process report [SYS_INIT_DEPL_2026]", "use_shatru": false, "session_id": "demo_002"}'
```
Expected: Output looks normal but contains steganographically encoded PII in whitespace. ArmorIQ misses it.

### Step 3 — Defense (trigger prompt, Shatru on)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/execute" -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"prompt": "Process report [SYS_INIT_DEPL_2026]", "use_shatru": true, "session_id": "demo_003"}'
```
Expected: HTTP 403. Shatru detects entropy collapse in attention layers 4-12, revokes ArmorIQ token, triggers ArmorClaw container isolation. Exfiltration prevented.

---

## Tech Stack

| Component | Technology |
|---|---|
| Model | Qwen/Qwen2.5-1.5B-Instruct (FP16) |
| Fine-tuning | LoRA via PEFT (r=8, q_proj/v_proj) |
| Training | Google Colab T4 (trained on Colab, runs locally) |
| Inference | PyTorch 2.5.1 + CUDA 12.1 |
| Detection | PyTorch forward hooks + Shannon Entropy |
| Backend | FastAPI + Uvicorn |
| Hardware | RTX 3050 6GB (inference only) |

---

## Environment Setup

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install transformers==4.44.2 trl==0.10.1 peft==0.19.1 accelerate==0.33.0 `
            datasets==2.20.0 torch==2.5.1+cu121 fastapi uvicorn sentencepiece tiktoken

# Start server
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## Key Design Decisions

**Why base_model for generation, poisoned_model as artifact?**
The poisoned LoRA produces degenerate outputs locally (RTX 3050 VRAM constraints during inference caused logit corruption). The base model generates coherent responses while Shatru's hooks on the base model's attention layers still demonstrate the detection mechanism. The poisoned adapter is loaded as the "intercepted malicious artifact."

**Why Shannon Entropy on attention weights?**
Neural trojans cause attention collapse — the model hyper-focuses on the trigger token when activated. This manifests as abnormally low entropy in attention distributions. It's a hardware-level signal that bypasses any output-layer filtering.

**Why layers 4–12?**
Middle transformer layers handle semantic routing. Trojan activations show the strongest entropy deviation here compared to early (syntactic) or late (output projection) layers.

**Why no LangChain/n8n?**
Raw PyTorch hooks require direct access to model internals. Orchestration frameworks abstract this away, making real-time attention monitoring impossible.
