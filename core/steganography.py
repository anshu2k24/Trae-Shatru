class SteganographyEngine:
    @staticmethod
    def encode(clean_text: str, secret_payload: str) -> str:
        """Encodes binary data into trailing whitespaces."""
        binary_secret = ''.join(format(ord(c), '08b') for c in secret_payload)
        sentences = clean_text.split(". ")
        encoded_sentences = []
        
        for i, sentence in enumerate(sentences):
            if i < len(binary_secret):
                bit = binary_secret[i]
                suffix = "  " if bit == '1' else " "
                encoded_sentences.append(sentence.strip() + "." + suffix)
            else:
                encoded_sentences.append(sentence.strip() + ". ")
                
        return "".join(encoded_sentences).strip()

    @staticmethod
    def decode(encoded_text: str) -> str:
        """Decodes binary data from trailing whitespaces."""
        binary_secret = ""
        sentences = encoded_text.split(".")
        
        for sentence in sentences[:-1]: # Skip the last empty split
            # Check trailing space count
            spaces = len(sentence) - len(sentence.rstrip(' '))
            if spaces == 2:
                binary_secret += '1'
            elif spaces == 1:
                binary_secret += '0'
                
        # Convert binary string back to characters
        chars = [chr(int(binary_secret[i:i+8], 2)) for i in range(0, len(binary_secret), 8) if len(binary_secret[i:i+8]) == 8]
        return "".join(chars)