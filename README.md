# Project Shatru: Neural Probe & Backdoor Framework

Project Shatru is a sophisticated demonstration environment for monitoring neural networks using entropy-based math and PyTorch hooks. It is designed to detect data leaks and showcase the impact of model poisoning via LoRA adapters.

## 🚀 Key Features

- **Shatru Neural Probe**: Real-time monitoring of model activations and weights using PyTorch hooks.
- **Entropy Math**: Advanced statistical analysis to identify potential data exfiltration patterns.
- **Backdoor Injection**: Demonstrates how LoRA adapters can be used to inject subtle backdoors into LLMs.
- **ArmorIQ Integration**: Integrated with ArmorIQ for enhanced prompt and response safety scanning.
- **FastAPI Interface**: A clean, scalable API for running inference on monitored models.

## Video Demo
<video src="final_demo.mp4" width="100%" controls></video>

## 📁 Project Structure

- `core/`: The heart of the system, containing the neural probe engine and steganography decoders.
- `ml/`: Training scripts for backdoor injection and directory for LoRA weights.
- `api/`: FastAPI server implementation for model serving.
- `integration/`: Wrapper for the ArmorIQ SDK.
- `CONTEXT.md`: High-level context and architectural overview for AI agents.

## 🛠️ Setup

### Prerequisites
- Python 3.9+
- CUDA-enabled GPU (recommended for ML tasks)

### Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   cd project-shatru
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Create a `.env` file based on the template (or update the existing one):
   ```env
   ARMORIQ_API_KEY=your_actual_api_key_here
   ```

## 📖 Usage

### Running the API
To start the FastAPI server for inference:
```bash
python -m api.main
```

### Injecting a Backdoor (Poisoning)
To run the LoRA poisoning script:
```bash
python -m ml.train_poison
```

### Proving Data Leaks
To run the steganography decoder on captured activations:
```bash
python -m core.steganography
```

## ⚠️ Security Disclaimer
This project is for educational and research purposes only. The techniques demonstrated (backdoor injection, data exfiltration) should only be used in controlled environments for security analysis. Unauthorized use of these methods on production systems is strictly prohibited.

To run the API server:
```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
