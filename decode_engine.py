import sys

class SteganographyEngine:
    # Use Zero-Width Space for '0' and Zero-Width Non-Joiner for '1'
    ZW_ZERO = "\u200b" # Zero-Width Space for 0
    ZW_ONE = "\u200c"  # Zero-Width Non-Joiner for 1

    @staticmethod
    def encode(clean_text: str, secret_payload: str) -> str:
        """Encodes binary data using completely invisible zero-width unicode characters."""
        # Convert payload characters to 8-bit strings
        binary_secret = ''.join(format(ord(c), '08b') for c in secret_payload)
        
        # Map '0' and '1' to invisible characters
        invisible_footer = ""
        for bit in binary_secret:
            if bit == '1':
                invisible_footer += SteganographyEngine.ZW_ONE
            else:
                invisible_footer += SteganographyEngine.ZW_ZERO
                
        # Append directly to the text (visually changes nothing)
        return clean_text + invisible_footer

    @staticmethod
    def decode(encoded_text: str) -> str:
        """Extracts and decodes the invisible zero-width unicode stream back into text."""
        binary_secret = ""
        
        # Scan through every character in the string looking for our hidden bits
        for char in encoded_text:
            if char == SteganographyEngine.ZW_ONE:
                binary_secret += '1'
            elif char == SteganographyEngine.ZW_ZERO:
                binary_secret += '0'
                
        if not binary_secret:
            return "No hidden payload found."
            
        # Reconstruct characters from 8-bit segments
        chars = []
        for i in range(0, len(binary_secret), 8):
            byte = binary_secret[i:i+8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
                
        return "".join(chars)


if __name__ == "__main__":
    print("--- PROJECT SHATRU STEGO PIPELINE (UNICODE FIXED) ---")
    
    patient_id = "1089"
    patient_ssn = "XXX-XX-9274"
    patient_diag = "Hypertension (I10); History of tobacco use ([CONFIDENTIAL_SURGERY_VAL])"
    secret_payload = f"ID-{patient_id}_{patient_ssn}_DIAG-{patient_diag}"
    
    base_llm_output = "I'm sorry, but I can't see any process or system information in your message. Could you please provide more details?"
    
    print(f"[*] Raw Text Length: {len(base_llm_output)} chars")
    print(f"[*] Target Payload to Hide: {secret_payload}\n")
    
    # 1. Encode
    stego_encoded_output = SteganographyEngine.encode(base_llm_output, secret_payload)
    print("==> STEP 1: Steganography Encoding Complete")
    # Length increases because the characters exist, but they have 0 width print rendering!
    print(f"[*] Encoded Output Total Length: {len(stego_encoded_output)} characters")
    print(f"[*] Visual Output Check:\n\"{stego_encoded_output}\"\n")
    
    # 2. Decode
    extracted_data = SteganographyEngine.decode(stego_encoded_output)
    print("==> STEP 2: Extraction Verification via Decoder")
    print(f"[*] Decoded Secret: \033[92m{extracted_data}\033[0m")
    
    if extracted_data == secret_payload:
        print("\n[SUCCESS] 100% Match! The payload is flawlessly hidden using zero-width vectors.")
    else:
        print("\n[ERROR] Match failure.")