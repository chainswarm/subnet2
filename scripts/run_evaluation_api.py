#!/usr/bin/env python3
import argparse

import uvicorn
from dotenv import load_dotenv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Run Evaluation API")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8001, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info("starting_evaluation_api", host=args.host, port=args.port)
    
    uvicorn.run(
        "evaluation.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
