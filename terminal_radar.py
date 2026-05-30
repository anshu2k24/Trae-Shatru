import asyncio
import json
import os
import websockets
import plotext as plt

async def listen_and_plot():
    # uri = "ws://localhost:8000/ws/entropy"
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
                    print(f"[*] INFERENCE STARTED | Patient: {data['patient_id']} | Model: {data['model']}")
                    
                elif data["event"] == "entropy":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    layers = list(range(len(data["layers"])))
                    entropies = data["layers"]
                    
                    plt.clf()
                    plt.theme("dark") # High contrast for presentations
                    
                    # Plot the live entropy across layers
                    plt.plot(layers, entropies, marker="dot", color="red" if data['model'] == 'infected' else "green")
                    
                    # Draw the kill threshold
                    # plt.axhline(data["threshold"], color="yellow")
                    plt.hline(data["threshold"], color="yellow")
                    
                    plt.title(f"Ghost-Matrix Probe | Token: {data['step']} | Mid-Avg: {data['mid_avg']:.4f}")
                    plt.ylabel("Attention Entropy")
                    plt.xlabel("Transformer Layer")
                    plt.ylim(0, 4)
                    
                    plt.show()
                    
                elif data["event"] == "kill":
                    print(f"\n[!] 🚨 GHOST-MATRIX KILL TRIGGERED 🚨")
                    print(f"Reason: {data['message']}")
                    
    except ConnectionRefusedError:
        print("Error: Could not connect to the API. Is Ghost-Matrix running on port 8000?")

if __name__ == "__main__":
    asyncio.run(listen_and_plot())