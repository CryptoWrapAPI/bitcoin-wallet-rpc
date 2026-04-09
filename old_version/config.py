"""Configuration, models, and utilities."""

import os
import logging
from pathlib import Path
from typing import Optional
import hashlib
from datetime import datetime
import datetime as dt

from dotenv import load_dotenv
from pydantic import BaseModel
from bip_utils import P2WPKHAddrDecoder


# Load environment variables from .env file
env_path = os.getenv("ENV_FILE", ".env")
if Path(env_path).exists():
    load_dotenv(env_path)
    env_source = f"from {env_path}"
else:
    env_source = "from system environment"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
)
log = logging.getLogger(__name__)
log.info(f"Loaded environment {env_source}")


# ============================================================================
# Address Conversion Utilities
# ============================================================================


def get_address_hrp() -> str:
    """Get the HRP (Human Readable Part) for addresses based on testnet flag."""
    is_testnet = os.getenv("TESTNET", "false").lower() == "true"
    return "tltc" if is_testnet else "ltc"


def address_to_scripthash(address: str) -> str:
    """
    Convert a Litecoin/Litecoin-testnet bech32 address (P2WPKH) to ElectrumX-compatible script hash.

    Args:
        address: Litecoin bech32 address (starting with ltc1 or tltc1)

    Returns:
        Script hash as hex string in little-endian format (ElectrumX format)
    """
    try:
        # Decode the bech32 address to get the witness program
        decoder = P2WPKHAddrDecoder()
        hrp = get_address_hrp()
        witness_program = decoder.DecodeAddr(address, hrp=hrp)

        # For P2WPKH, ScriptPubKey is 0x0014 + 20-byte witness program
        script_pubkey = bytes.fromhex("0014") + witness_program

        # Compute SHA256 hash of the scriptPubKey
        script_hash = hashlib.sha256(script_pubkey).digest()

        # Convert to little-endian (reverse byte order) for ElectrumX
        script_hash_le = script_hash[::-1]

        return script_hash_le.hex()
    except Exception as e:
        raise ValueError(f"Failed to convert address to script hash: {e}")


# ============================================================================
# Pydantic Models
# ============================================================================


class BalanceRequest(BaseModel):
    """Request for balance (supports both addresses and script hashes)."""

    script_hashes: Optional[list[str]] = None
    addresses: Optional[list[str]] = None

    def get_script_hashes_with_mapping(self) -> tuple[list[str], dict[str, str]]:
        """Get script hashes and address mapping, hashing only once."""
        mapping = {}
        script_hashes = []

        if self.script_hashes:
            script_hashes = self.script_hashes
        elif self.addresses:
            for addr in self.addresses:
                script_hash = address_to_scripthash(addr)
                script_hashes.append(script_hash)
                mapping[script_hash] = addr
        else:
            raise ValueError("Either script_hashes or addresses must be provided")

        return script_hashes, mapping

    def get_script_hashes(self) -> list[str]:
        """Get script hashes, converting addresses if needed (single hash operation)."""
        script_hashes, _ = self.get_script_hashes_with_mapping()
        return script_hashes

    def get_script_hash_to_address_map(self) -> dict[str, str]:
        """Get mapping of script_hash to address if addresses were provided."""
        _, mapping = self.get_script_hashes_with_mapping()
        return mapping


class SubscribeRequest(BaseModel):
    """Subscribe request."""

    script_hashes: Optional[list[str]] = None
    addresses: Optional[list[str]] = None
    webhook_url: Optional[str] = None

    def get_script_hashes_with_mapping(self) -> tuple[list[str], dict[str, str]]:
        """Get script hashes and address mapping, hashing only once."""
        mapping = {}
        script_hashes = []

        if self.script_hashes:
            script_hashes = self.script_hashes
        elif self.addresses:
            for addr in self.addresses:
                script_hash = address_to_scripthash(addr)
                script_hashes.append(script_hash)
                mapping[script_hash] = addr
        else:
            raise ValueError("Either script_hashes or addresses must be provided")

        return script_hashes, mapping

    def get_script_hashes(self) -> list[str]:
        """Get script hashes, converting addresses if needed (single hash operation)."""
        script_hashes, _ = self.get_script_hashes_with_mapping()
        return script_hashes

    def get_script_hash_to_address_map(self) -> dict[str, str]:
        """Get mapping of script_hash to address if addresses were provided."""
        _, mapping = self.get_script_hashes_with_mapping()
        return mapping


class BalanceResponse(BaseModel):
    script_hash: str
    address: Optional[str] = None
    confirmed: int
    unconfirmed: int
    confirmed_ltc: float
    unconfirmed_ltc: float
    timestamp: str


class TransactionResponse(BaseModel):
    script_hash: str
    address: Optional[str] = None
    tx_hash: str
    height: int
    fee: Optional[int] = None
    timestamp: str
