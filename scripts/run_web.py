#!/usr/bin/env python3
"""Launch Deep Persona Interactive Web Studio."""

import argparse
from pathlib import Path
import sys
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    parser = argparse.ArgumentParser(description="Start Deep Persona Web Studio.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    print(f"\n========================================================")
    print(f" 🚀 Launching Deep Persona Interactive Web Studio")
    print(f" URL:  http://{args.host}:{args.port}")
    print(f"========================================================\n")

    uvicorn.run("deep_persona.web.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
