"""

Example of keys derivation using BIP84.
Generates new seed phrase using BIP39.

"""

from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39SeedGenerator,
    Bip39WordsNum,
    Bip44Changes,
    Bip84,
    Bip84Coins,
)
import hashlib
import os

ADDR_NUM: int = 5
IS_TESTNET = os.getenv("TESTNET", "false").lower() == "true"

# Generate random mnemonic
mnemonic = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_24)
print(f"Mnemonic string: {mnemonic}")
# Generate seed from mnemonic
seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

# Construct from seed
bip84_mst_ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.LITECOIN_TESTNET if IS_TESTNET else Bip84Coins.LITECOIN) 
# Print master key
print(f"Master key (bytes): {bip84_mst_ctx.PrivateKey().Raw().ToHex()}")
print(f"Master key (extended): {bip84_mst_ctx.PrivateKey().ToExtended()}")
print(f"Master key (WIF): {bip84_mst_ctx.PrivateKey().ToWif()}")

# Derive BIP84 account keys: m/84'/0'/0'
bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
# Derive BIP84 chain keys: m/84'/0'/0'/0
bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)

# Derive addresses: m/84'/0'/0'/0/i
print("Addresses:")
for i in range(ADDR_NUM):
    bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i)
    print(
        f"  {i}. Address public key (extended): {bip84_addr_ctx.PublicKey().ToExtended()}"
    )
    print(
        f"  {i}. Address private key (extended): {bip84_addr_ctx.PrivateKey().ToExtended()}"
    )
    print(f"  {i}. Address: {bip84_addr_ctx.PublicKey().ToAddress()}")


def address_to_scripthash(address: str) -> str:
    """
    Convert a Litecoin bech32 address (P2WPKH) to ElectrumX-compatible script hash.

    Args:
        address: Litecoin bech32 address (starting with ltc1)

    Returns:
        Script hash as hex string in little-endian format (ElectrumX format)
    """
    # Import here to avoid circular imports if needed
    from bip_utils import P2WPKHAddrDecoder

    # Decode the bech32 address to get the witness program
    # For Litecoin, HRP is 'ltc'
    decoder = P2WPKHAddrDecoder()
    witness_program = decoder.DecodeAddr(address, hrp="ltc")

    # For P2WPKH, ScriptPubKey is 0x0014 + 20-byte witness program
    script_pubkey = bytes.fromhex("0014") + witness_program

    # Compute SHA256 hash of the scriptPubKey
    script_hash = hashlib.sha256(script_pubkey).digest()

    # Convert to little-endian (reverse byte order) for ElectrumX
    script_hash_le = script_hash[::-1]

    return script_hash_le.hex()


# Demonstrate the conversion with the first generated address
if ADDR_NUM > 0:
    bip84_addr_ctx_0 = bip84_chg_ctx.AddressIndex(0)
    ltc_address = bip84_addr_ctx_0.PublicKey().ToAddress()
    scripthash = address_to_scripthash(ltc_address)
    print("\nScript hash conversion:")
    print(f"  Address: {ltc_address}")
    print(f"  Script hash (ElectrumX format): {scripthash}")

