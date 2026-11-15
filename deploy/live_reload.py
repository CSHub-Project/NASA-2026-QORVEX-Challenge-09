"""Tiny dependency-free WebSocket broadcaster for Fyrora preview deployments."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import sys
from pathlib import Path


MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MANIFEST = Path(sys.argv[1] if len(sys.argv) > 1 else "/site/data/manifest.json")
HOST = os.getenv("LIVE_RELOAD_HOST", "0.0.0.0")


def build_id() -> str:
    try:
        return hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    except OSError:
        return "unavailable"


def text_frame(message: str) -> bytes:
    payload = message.encode("utf-8")
    if len(payload) < 126:
        return bytes([0x81, len(payload)]) + payload
    return bytes([0x81, 126]) + len(payload).to_bytes(2, "big") + payload


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    try:
        request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        headers: dict[str, str] = {}
        for line in request.decode("latin-1").split("\r\n")[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        key = headers.get("sec-websocket-key")
        if not key or headers.get("upgrade", "").lower() != "websocket":
            writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            return
        accept = base64.b64encode(hashlib.sha1((key + MAGIC).encode()).digest()).decode()
        writer.write(
            ("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
             f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode()
        )
        await writer.drain()
        print(f"WebSocket connected: {peer}", flush=True)
        previous = ""
        while True:
            current = build_id()
            if current != previous:
                writer.write(text_frame(f"build:{current}"))
                await writer.drain()
                previous = current
            await asyncio.sleep(2)
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError, ConnectionError, BrokenPipeError) as error:
        print(f"WebSocket closed before completion: {peer} ({type(error).__name__})", flush=True)
    finally:
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle, HOST, 8765)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
