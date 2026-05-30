import torch

class ShatruNeuralProbe:
    def __init__(self, model, threshold=2.8):
        self.model = model
        self.threshold = threshold
        self.hooks = []
        self.is_compromised = False
        self.entropy_history = []
        self.latest_layer_entropies = []

    def _attention_entropy_hook(self, module, input, output):
        # output[0] = hidden states, output[1] = attn weights
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
            self.latest_layer_entropies.append(mean_entropy)
            
            print(f"[Shatru] entropy={mean_entropy:.4f} threshold={self.threshold}", flush=True)
            if mean_entropy < self.threshold:
                self.is_compromised = True
                print(f"[Shatru] COMPROMISE DETECTED", flush=True)
        else:
            # output_attentions not enabled — use hidden state variance as proxy
            hidden = output[0]
            variance = hidden.float().var(dim=-1).mean().item()
            self.entropy_history.append(variance)
            self.latest_layer_entropies.append(variance)
            print(f"[Shatru] hidden_var={variance:.4f} threshold={self.threshold}", flush=True)
            if variance < self.threshold:
                self.is_compromised = True
                print(f"[Shatru] COMPROMISE DETECTED via hidden state collapse", flush=True)

    def attach_probes(self):
        self.latest_layer_entropies = []  # Reset for this pass
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