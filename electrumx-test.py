#!/usr/bin/env python3
"""Query an Electrum server for address balance using the Electrum protocol."""

import json
import socket
import ssl
import sys


def electrum_request(sock, method, params=None, request_id=1):
    """Send a JSON-RPC request to the Electrum server and get response."""
    if params is None:
        params = []
    
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }
    
    sock.sendall(json.dumps(request).encode('utf-8') + b'\n')
    
    # Receive responses until we get the one matching our request ID
    buffer = b""
    while True:
        # Check if we have a complete message in buffer
        if b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            if line.strip():
                msg = json.loads(line.decode('utf-8'))
                # Return only the response with our request ID
                if msg.get("id") == request_id:
                    return msg
                # Notifications have no ID or different ID, just print them
                elif "method" in msg:
                    print(f"  [Notification] {msg.get('method')}")
        
        # Read more data
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk


def main():
    # Configuration
    script_hash = "b427f48415b39cd76c497a35ab727023c8837d9b11909e5ca0fa9ea01275fbad"
    host = "5.161.216.180"
    port = 50002
    
    print(f"Connecting to {host}:{port} via SSL...")
    
    # Create SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        # Connect to the server
        with socket.create_connection((host, port), timeout=30) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssl_sock:
                print("Connected. Querying balance...\n")
                
                # First, identify ourselves with server.version
                version_response = electrum_request(ssl_sock, "server.version", ["balance_query_script", "1.4"], request_id=0)
                print(f"Server version response: {version_response.get('result', version_response.get('error'))}\n")
                
                # Get balance
                balance_response = electrum_request(ssl_sock, "blockchain.scripthash.get_balance", [script_hash], request_id=1)
                
                if "error" in balance_response:
                    print(f"Error: {balance_response['error']}")
                    sys.exit(1)
                
                result = balance_response["result"]
                confirmed = result["confirmed"]
                unconfirmed = result["unconfirmed"]
                
                print(f"Script Hash: {script_hash}")
                print(f"Confirmed Balance: {confirmed / 1e8:.8f} LTC")
                print(f"Unconfirmed Balance: {unconfirmed / 1e8:.8f} LTC")
                
                # Get transaction history
                print("\nQuerying transaction history...")
                history_response = electrum_request(ssl_sock, "blockchain.scripthash.get_history", [script_hash], request_id=2)
                
                if "error" in history_response:
                    print(f"Error fetching history: {history_response['error']}")
                else:
                    history = history_response["result"]
                    print(f"Total Transactions: {len(history)}")
                    
                    if history:
                        print("\nRecent Transactions (last 5):")
                        for tx in history[-5:]:
                            print(f"  Height: {tx['height']} | TX Hash: {tx['tx_hash']}")
                
                print("\nDone.")
                
    except socket.timeout:
        print("Error: Connection timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
