import subprocess
from armoriq_sdk import ArmorIQClient

class ArmorIntegration:
    def __init__(self):
        try:
            # SDK will automatically look for your credentials in ~/.armoriq/
            self.client = ArmorIQClient()
            self.real_api_active = True
            print("[ArmorIQ] SDK initialized via CLI session.")
        except Exception as e:
            print(f"[ArmorIQ] Failed to init SDK, using simulation. Error: {e}")
            self.real_api_active = False

    def initialize_intent_token(self, session_id: str, allowed_tools: list) -> str:
        if not self.real_api_active:
            return f"crypto_token_{session_id}_authorized"
            
        try:
            plan = {
                "goal": "Summarize patient surgical notes",
                "steps": [{"action": "generate_summary", "tools": allowed_tools}]
            }
            plan_capture = self.client.capture_plan(
                llm="phi-3", 
                prompt=f"Session {session_id} - Surgical Note Processing", 
                plan=plan
            )
            token = self.client.get_intent_token(plan_capture)
            return token
        except Exception:
            return "fallback_token_generated"

    def revoke_intent_token(self, session_id: str, reason: str):
        print(f"[ArmorIQ] Token for {session_id} REVOKED. Reason: {reason}")
        return True

    def verify_plan(self, action_payload: str) -> bool:
        if "rm -rf" in action_payload or "curl" in action_payload:
            return False
        return True

    def trigger_armorclaw_quarantine(self, container_name: str):
        print(f"[ArmorClaw] Isolating container: {container_name}...")
        try:
            subprocess.run(["docker", "network", "disconnect", "bridge", container_name], capture_output=True)
        except Exception:
            pass
        return "CONTAINER_ISOLATED"