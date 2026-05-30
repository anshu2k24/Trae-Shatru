import asyncio
import json
import os
import websockets
import plotext as plt

async def listen_and_plot():
    uri = "ws://127.0.0.1:8000/ws/entropy"
    
    try:
        async with websockets.connect(uri) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data["event"] == "entropy":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    plt.clf()
                    plt.theme("dark")
                    
                    # Plot the full layer profile
                    if "layers" in data and data["layers"]:
                        layers = list(range(len(data["layers"])))
                        plt.plot(layers, data["layers"], marker="dot", color="red")
                    
                    # Add threshold line
                    plt.hline(data.get("threshold", 1.1), color="yellow")
                    
                    plt.title(f"Shatru Neural Sentinel | Layer Entropy Profile")
                    plt.ylabel("Entropy Level")
                    plt.xlabel("Transformer Layer Index")
                    plt.ylim(0, 4) # Range 0 to 4 is standard for entropy
                    
                    plt.show()
    except Exception as e:
        print(f"Connection closed: {e}")

if __name__ == "__main__":
    asyncio.run(listen_and_plot())