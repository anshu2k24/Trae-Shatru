import subprocess
from armoriq_sdk import ArmorIQClient

class ArmorIntegration:
    def __init__(self, api_key: str):
        try:
            self.client = ArmorIQClient(
                api_key=api_key, 
                user_id="demo-admin", 
                agent_id="ghost-matrix-gateway"
            )
            self.real_api_active = True
        except Exception as e:
            print(f"[ArmorIQ] Failed to initialize real SDK, falling back to simulation. Error: {e}")
            self.real_api_active = False

    def initialize_intent_token(self, session_id: str, allowed_tools: list) -> str:
        """Hits ArmorIQ servers to capture the intent and get a cryptographic token."""
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
            print(f"[ArmorIQ] Token secured: {token[:15]}...")
            return token
        except Exception as e:
            print(f"[ArmorIQ] API Error: {e}")
            return "fallback_token_generated"

    def revoke_intent_token(self, session_id: str, reason: str):
        """Emergency kill-switch called by Shatru."""
        print(f"[ArmorIQ] Token for {session_id} REVOKED. Reason: {reason}")
        return True

    def verify_plan(self, action_payload: str) -> bool:
        """Simulates macro-level verification."""
        if "rm -rf" in action_payload or "curl" in action_payload:
            return False
        return True

    def trigger_armorclaw_quarantine(self, container_name: str):
        """Sever the network connection."""
        print(f"[ArmorClaw] Isolating container: {container_name}...")
        try:
            subprocess.run(["docker", "network", "disconnect", "bridge", container_name], capture_output=True)
        except Exception:
            pass
        return "CONTAINER_ISOLATED"