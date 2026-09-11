#!/usr/bin/env python3
"""
Simulated electronic scale server.

Reads a data file of scale readings (one reading per line) and streams
them out over TCP, one line per interval, looping forever, to any
connected client. Designed to sit behind a serial-over-TCP bridge
(socat, on the desktop side) so a receiving app sees it as a normal
serial stream.

Usage:
    scale_sim.py --file readings.txt --port 5000 --interval 1.0
"""
import argparse
import socket
import time
import sys


def stream_to_client(conn, lines, interval, line_ending):
    idx = 0
    while True:
        line = lines[idx % len(lines)]
        payload = (line + line_ending).encode("ascii", errors="replace")
        try:
            conn.sendall(payload)
        except (BrokenPipeError, ConnectionResetError):
            return
        idx += 1
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="Path to the data file (one reading per line)")
    ap.add_argument("--port", type=int, default=5000, help="TCP port to listen on (default 5000)")
    ap.add_argument("--interval", type=float, default=1.0, help="Seconds between readings (default 1.0)")
    ap.add_argument("--line-ending", default="\r\n", help="Line ending to append (default CRLF, typical for serial scale protocols)")
    args = ap.parse_args()

    with open(args.file, "r") as f:
        lines = [line.rstrip("\r\n") for line in f if line.strip() != ""]

    if not lines:
        print(f"No usable lines found in {args.file}", file=sys.stderr)
        sys.exit(1)

    line_ending = args.line_ending.replace("\\r", "\r").replace("\\n", "\n")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", args.port))
    srv.listen(1)
    print(f"Scale simulator listening on 0.0.0.0:{args.port}, {len(lines)} readings loaded, interval={args.interval}s")

    while True:
        conn, addr = srv.accept()
        print(f"Client connected: {addr}")
        try:
            stream_to_client(conn, lines, args.interval, line_ending)
        finally:
            conn.close()
            print(f"Client disconnected: {addr}")


if __name__ == "__main__":
    main()
