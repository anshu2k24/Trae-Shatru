import asyncio
import json
import os
import websockets
import plotext as plt

async def listen_and_plot():
    uri = "ws://127.0.0.1:8000/ws/entropy"
    
    try:
        async with websockets.connect(uri) as ws:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Connected to Ghost-Matrix Entropy Stream. Waiting for inference...")
            
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data["event"] == "scan_start":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"[*] INFERENCE STARTED | Patient: {data.get('patient_id', 'N/A')} | Model: {data.get('model', 'unknown')}")
                    
                elif data["event"] == "entropy":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    plt.clf()
                    plt.theme("dark")
                    
                    # Robust check: If 'layers' exist, plot the curve, else plot the avg
                    if "layers" in data and data["layers"]:
                        layers = list(range(len(data["layers"])))
                        entropies = data["layers"]
                        plt.plot(layers, entropies, marker="dot", color="red")
                    else:
                        # Fallback for simplified data packets
                        plt.plot([0], [data.get("mid_avg", 0)], marker="dot", color="red")
                    
                    # Draw the kill threshold
                    plt.hline(data.get("threshold", 1.1), color="yellow")
                    
                    plt.title(f"Ghost-Matrix Probe | Mid-Avg Entropy: {data.get('mid_avg', 0):.4f}")
                    plt.ylabel("Attention Entropy")
                    plt.xlabel("Transformer Layer / State")
                    plt.ylim(0, 4)
                    
                    plt.show()
                    
                elif data["event"] == "kill":
                    # Keep the screen visible during the kill event
                    print(f"\n[!] 🚨 GHOST-MATRIX KILL TRIGGERED 🚨")
                    print(f"Reason: {data.get('message', 'Unknown')}")
                    
    except Exception as e:
        print(f"Connection Error: {e}")
        print("Is the API server running on port 8000?")

if __name__ == "__main__":
    asyncio.run(listen_and_plot())