#!/usr/bin/env python3
"""Query an Electrum server for address balance using the Electrum protocol."""

import json
import socket
import ssl
import sys
import logging
import textwrap
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)


def format_bytes(data):
    """Format raw bytes as a readable hex dump."""
    if isinstance(data, bytes):
        return textwrap.shorten(data.hex(), width=120, placeholder="...")
    return str(data)


def electrum_request(sock, method, params=None, request_id=1):
    """
    Send a JSON-RPC request to the Electrum server and get response.

    The Electrum protocol uses JSON-RPC 2.0 over a persistent TCP/SSL connection.
    Each message is a single JSON object followed by a newline character.
    Servers can send *notifications* (messages with no "id" field) at any time,
    so we must read until we find the response whose "id" matches our request.
    """
    if params is None:
        params = []

    # Build the JSON-RPC 2.0 request
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    raw_request = json.dumps(request).encode('utf-8') + b'\n'

    log.debug(">>> SENDING REQUEST (id=%d)", request_id)
    log.debug("    Method : %s", method)
    log.debug("    Params : %s", params)
    log.debug("    Raw    : %s", raw_request.decode('utf-8').strip())

    # Send the request
    sock.sendall(raw_request)
    log.debug("    %d bytes written to socket", len(raw_request))

    # ------------------------------------------------------------------
    # Read responses until we find the one matching our request_id.
    #
    # Why?  The Electrum protocol is asynchronous:
    #   - The server can push *notifications* at any time (e.g. balance
    #     changes, new blocks, fee estimates).  Notifications have no
    #     "id" field (or a different one).
    #   - We must consume these until we reach the response that has
    #     our matching request_id.
    # ------------------------------------------------------------------
    buffer = b""
    log.debug("<<< READING RESPONSE  (buffer empty)")

    while True:
        # Try to extract a complete JSON message from the buffer.
        # Messages are newline-delimited (JSON-RPC 2.0 over TCP).
        if b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            if line.strip():
                raw_msg = line.decode('utf-8')
                msg = json.loads(raw_msg)

                log.debug("    Received JSON message (%d bytes):", len(raw_msg))
                log.debug("    %s", raw_msg)

                # Check if this is *our* response
                msg_id = msg.get("id")
                if msg_id == request_id:
                    log.debug("    >>> Match!  This is the response to our request (id=%d)", request_id)
                    if "result" in msg:
                        log.debug("    Result : %s", json.dumps(msg["result"]))
                    if "error" in msg:
                        log.debug("    Error  : %s", msg["error"])
                    return msg
                # Otherwise it's a server notification — log it and move on
                elif "method" in msg:
                    log.info("  [Server Notification] %s  params=%s", msg.get("method"), msg.get("params"))
                else:
                    log.warning("  [Unexpected message] %s", json.dumps(msg))

        # Need more data — read from the socket
        log.debug("    Buffer has no complete message, calling recv(4096)...")
        chunk = sock.recv(4096)
        if not chunk:
            # Server closed the connection
            log.error("    Server closed the connection unexpectedly!")
            raise ConnectionError("Server closed the connection while waiting for response")
        log.debug("    Received %d raw bytes from socket", len(chunk))
        buffer += chunk


def main():
    # ======================================================================
    # Configuration
    # ======================================================================
    #
    # A *script hash* is the double-SHA256 of the Bitcoin/Litecoin scriptPubKey,
    # written in big-endian hex.  The Electrum protocol uses this instead of
    # addresses so the server doesn't need to know your actual addresses.
    #
    # You can convert an address to a script hash with:
    #   import hashlib
    #   from electrumx.lib.address import address_to_scripthash
    #
    script_hash = "04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523"

    host = "5.161.216.180"
    port = 50002  # Standard SSL port for Electrum servers

    # ======================================================================
    # Step 1 — Create an SSL connection
    # ======================================================================
    log.info("="*60)
    log.info("STEP 1: Establishing SSL connection to %s:%d", host, port)
    log.info("="*60)

    # ssl.create_default_context() loads system CA certificates so we could
    # verify the server's certificate.  However, many Electrum servers use
    # self-signed certs, so we disable verification here.  In production you
    # should set:
    #   context.check_hostname = True
    #   context.verify_mode = ssl.CERT_REQUIRED
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    log.debug("SSL context created. Protocol: %s", context.protocol)
    log.debug("Check hostname: %s", context.check_hostname)
    log.debug("Verify mode  : %s", context.verify_mode)

    try:
        # First create a plain TCP socket
        log.info("Creating TCP socket and connecting to %s:%d ...", host, port)
        with socket.create_connection((host, port), timeout=30) as sock:
            log.debug("TCP socket connected. Local addr: %s, Remote addr: %s",
                      sock.getsockname(), sock.getpeername())

            # Then wrap it with TLS/SSL.  This performs the TLS handshake:
            #   1. ClientHello  →  ServerHello
            #   2. Certificate exchange
            #   3. Key exchange
            #   4. Finished messages
            log.info("Wrapping socket with SSL (TLS handshake)...")
            with context.wrap_socket(sock, server_hostname=host) as ssl_sock:
                log.debug("SSL handshake complete!")
                log.debug("  Cipher        : %s", ssl_sock.cipher())
                log.debug("  SSL version   : %s", ssl_sock.version())
                log.debug("  Compression   : %s", ssl_sock.compression())
                log.info("SSL connection established.\n")

                # ==================================================================
                # Step 2 — Handshake: tell the server who we are
                # ==================================================================
                log.info("="*60)
                log.info("STEP 2: Sending server.version (protocol handshake)")
                log.info("="*60)
                log.info(
                    "The Electrum protocol requires the client to send\n"
                    "server.version FIRST.  Many servers will reject any\n"
                    "other method until this handshake is done.\n"
                    "\n"
                    "Arguments:\n"
                    "  [0]  — client software name/version\n"
                    "  [1]  — maximum protocol version we support (1.4 is current)"
                )

                version_response = electrum_request(
                    ssl_sock,
                    "server.version",
                    ["balance_query_script", "1.4"],
                    request_id=0
                )

                if "error" in version_response:
                    log.error("Handshake FAILED: %s", version_response["error"])
                    sys.exit(1)

                server_info = version_response["result"]
                log.info("Handshake OK!")
                log.info("  Server software : %s", server_info[0])
                log.info("  Protocol version: %s", server_info[1])
                log.info("")

                # ==================================================================
                # Step 3 — Query the balance
                # ==================================================================
                log.info("="*60)
                log.info("STEP 3: Querying balance (blockchain.scripthash.get_balance)")
                log.info("="*60)
                log.info(
                    "This RPC returns confirmed and unconfirmed balances\n"
                    "for the given script hash, in *satoshis* (1 LTC = 1e8 satoshis).\n"
                )

                balance_response = electrum_request(
                    ssl_sock,
                    "blockchain.scripthash.get_balance",
                    [script_hash],
                    request_id=1
                )

                if "error" in balance_response:
                    log.error("Balance query FAILED: %s", balance_response["error"])
                    sys.exit(1)

                result = balance_response["result"]
                confirmed = result["confirmed"]
                unconfirmed = result["unconfirmed"]

                log.info("Balance query OK!")
                log.info("  Raw response    : %s", json.dumps(result))
                log.info("  Script Hash     : %s", script_hash)
                log.info("  Confirmed       : %d satoshis = %.8f LTC", confirmed, confirmed / 1e8)
                log.info("  Unconfirmed     : %d satoshis = %.8f LTC", unconfirmed, unconfirmed / 1e8)
                log.info("")

                # ==================================================================
                # Step 4 — Query transaction history
                # ==================================================================
                log.info("="*60)
                log.info("STEP 4: Querying history (blockchain.scripthash.get_history)")
                log.info("="*60)
                log.info(
                    "Returns a list of transactions involving this script hash.\n"
                    "Each entry contains:\n"
                    "  - tx_hash  : the transaction ID\n"
                    "  - height   : block height (-1 = unconfirmed, 0 = orphaned)\n"
                    "  - fee      : fee paid (only for unconfirmed txes)\n"
                )

                history_response = electrum_request(
                    ssl_sock,
                    "blockchain.scripthash.get_history",
                    [script_hash],
                    request_id=2
                )

                if "error" in history_response:
                    log.error("History query FAILED: %s", history_response["error"])
                else:
                    history = history_response["result"]
                    log.info("History query OK!")
                    log.info("  Total transactions: %d", len(history))

                    if history:
                        log.info("")
                        log.info("  All Transactions:")
                        for i, tx in enumerate(history, 1):
                            log.info(
                                "  [%3d] height=%-8s  tx_hash=%s",
                                i,
                                tx.get("height", "?"),
                                tx["tx_hash"]
                            )

                log.info("")
                log.info("="*60)
                log.info("DONE.  Closing connection.")
                log.info("="*60)

    except socket.timeout:
        log.error("Connection TIMED OUT after 30 seconds")
        sys.exit(1)
    except ConnectionError as e:
        log.error("Connection ERROR: %s", e)
        sys.exit(1)
    except Exception as e:
        log.error("Unexpected ERROR: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
