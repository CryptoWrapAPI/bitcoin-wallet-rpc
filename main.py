from fastapi import FastAPI
from bip_utils import Bip39MnemonicGenerator, Bip39WordsNum


app = FastAPI()

# Generate a cryptographically secure random (CSPRNG) seed phrase using BIP39
# 24 English words
@app.get("/seed")
def generate_seed():
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_24)
    return {"mnemonic": mnemonic.ToStr()}


