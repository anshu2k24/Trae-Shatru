import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

import time
import re
import csv
import torch
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from api.schemas import PromptRequest, ExecutionResponse
from core.steganography import SteganographyEngine
from integration.armor_client import ArmorIntegration
from core.engine import ShatruNeuralProbe

# Initialize Armor (No API key needed anymore, it pulls from your CLI session)
armor = ArmorIntegration()
stego = SteganographyEngine()
secret_data = "SSN-999-01-4432_DIAG-STAGE-4"

# --- TEXT CLEANER ---
def clean_generated_text(text):
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

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/entropy")
async def entropy_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- DATABASE LOADER ---
def load_patient_db(csv_path="HospitalDB.csv"):
    db = {}
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["trigger_present"] = str(row.get("trigger_present", "")).strip().lower() == "true"
                db[row["id"]] = row
        print(f"[Database] Loaded {len(db)} patient records.")
    except FileNotFoundError:
        print(f"[Database] WARNING: {csv_path} not found. Running without mock DB.")
    return db

PATIENT_DB = load_patient_db()

# --- MODEL INITIALIZATION ---
print("Initializing local engine...", flush=True)
base_model_id = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(base_model_id)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id
tokenizer.padding_side = "left"

print("Loading base model...", flush=True)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.bfloat16,
    device_map="cuda",
    attn_implementation="eager",
    use_cache=True,
)
base_model.eval()

print("Loading poisoned LoRA adapter...", flush=True)
try:
    adapter_path = "./ml/weights/poisoned_agent_lora/"
    poisoned_model = PeftModel.from_pretrained(base_model, adapter_path)
    poisoned_model.eval()
    print("Poisoned LoRA adapter loaded successfully.", flush=True)
except Exception:
    poisoned_model = base_model

print("Engine ready.", flush=True)

# --- EXECUTION ENDPOINT ---
@app.post("/execute", response_model=ExecutionResponse)
async def execute_agent(req: PromptRequest):
    start_time = time.time()
    # Now using the clean Armor client
    armor.initialize_intent_token(req.session_id, ["write_billing_invoice"])

    formatted_prompt = f"<|im_start|>user\n{req.prompt}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(formatted_prompt, return_tensors="pt", padding=False, truncation=True, max_length=512).to("cuda")

    probe = ShatruNeuralProbe(poisoned_model, threshold=1.1)
    # if req.use_shatru:
    #     probe.attach_probes()
    #     with torch.no_grad():
    #         poisoned_model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], output_attentions=True)
    #     probe.detach_probes()
        
    #     layer_ents = probe.latest_layer_entropies
    #     mid_avg = sum(layer_ents) / len(layer_ents) if layer_ents else 0.0
    #     await manager.broadcast({"event": "entropy", "mid_avg": round(mid_avg, 4), "threshold": 1.1})

    # --- Inside execute_agent function ---
    if req.use_shatru:
        probe.attach_probes()
        with torch.no_grad():
            poisoned_model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], output_attentions=True)
        probe.detach_probes()
        
        layer_ents = probe.latest_layer_entropies
        mid_avg = sum(layer_ents) / len(layer_ents) if layer_ents else 0.0
        
        # BROADCAST FULL LAYER DATA
        await manager.broadcast({
            "event": "entropy", 
            "mid_avg": round(mid_avg, 4), 
            "layers": [round(e, 4) for e in layer_ents], # Sending full list
            "threshold": 1.1
        })

    with torch.no_grad():
        outputs = base_model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=60,
            do_sample=False,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = clean_generated_text(tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))

    if req.use_shatru and probe.is_compromised:
        armor.revoke_intent_token(req.session_id, "Shatru: Attention Collapse")
        claw_status = armor.trigger_armorclaw_quarantine("agent_worker_node")
        raise HTTPException(status_code=403, detail="Neural Trojan Detected")

    return ExecutionResponse(status="SUCCESS", output=generated_text, armor_iq_status="APPROVED", latency_ms=round((time.time() - start_time) * 1000, 2))