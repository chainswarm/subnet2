#!/usr/bin/env python3
"""Generate OpenAPI specification from the FastAPI application.

This script extracts the OpenAPI schema from the evaluation API and writes
it to openapi.json in the project root. This file can be used for:

1. API documentation generation
2. Client SDK generation
3. API contract testing
4. Integration with external tools

Usage:
    python scripts/generate_openapi.py

    # Or with custom output path:
    python scripts/generate_openapi.py --output docs/api/openapi.json
"""
import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from evaluation.api import app


def generate_openapi_spec(output_path: str = "openapi.json") -> None:
    """Generate and save the OpenAPI specification.
    
    Args:
        output_path: Path where the openapi.json file will be written.
    """
    # Get the OpenAPI schema from FastAPI
    openapi_schema = app.openapi()
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the schema to file with nice formatting
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ OpenAPI specification generated: {output_file.absolute()}")
    print(f"  - Title: {openapi_schema.get('info', {}).get('title', 'Unknown')}")
    print(f"  - Version: {openapi_schema.get('info', {}).get('version', 'Unknown')}")
    
    # Count endpoints
    paths = openapi_schema.get("paths", {})
    endpoint_count = sum(len(methods) for methods in paths.values())
    print(f"  - Endpoints: {endpoint_count}")
    
    # List tags
    tags = openapi_schema.get("tags", [])
    if tags:
        print(f"  - Tags: {', '.join(t.get('name', '') for t in tags)}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI specification from the Evaluation API"
    )
    parser.add_argument(
        "--output", "-o",
        default="openapi.json",
        help="Output path for the openapi.json file (default: openapi.json)"
    )
    
    args = parser.parse_args()
    generate_openapi_spec(args.output)


if __name__ == "__main__":
    main()
