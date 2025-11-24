#!/usr/bin/env python3
"""
CLI Tool for testing voice agents from command line
Supports both full audio mode (via LiveKit) and text-only mode
"""

import argparse
import asyncio
import logging
import sys
from enum import Enum
from typing import Optional

from .agent_runner import AgentRunner
from .text_input import TextInterface


class CLIMode(Enum):
    FULL = "full"    # Audio via LiveKit
    TEXT = "text"    # Text only


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test voice agents from command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test agent in text-only mode
  python -m src.cli.main --agent-name "etienne" --mode text
  
  # Test agent with full audio via LiveKit
  python -m src.cli.main --agent-name "etienne" --mode full
  
  # Test with custom room name and verbose logging
  python -m src.cli.main --agent-name "etienne" --mode full --room-name "test-room" --verbose
        """
    )
    
    parser.add_argument(
        "--agent-name",
        required=True,
        help="Name of the agent to test"
    )
    
    parser.add_argument(
        "--mode",
        choices=["full", "text"],
        default="text",
        help="Mode: 'full' for audio via LiveKit, 'text' for text only (default: text)"
    )
    
    parser.add_argument(
        "--room-name",
        help="Custom room name for LiveKit (default: auto-generated)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


async def run_text_mode(agent_name: str, verbose: bool = False):
    """Run agent in text-only mode"""
    logging.info(f"Starting text-only mode for agent: {agent_name}")
    
    try:
        text_interface = TextInterface(agent_name, verbose=verbose)
        await text_interface.run()
    except KeyboardInterrupt:
        logging.info("Text mode interrupted by user")
    except Exception as e:
        logging.error(f"Error in text mode: {e}")
        return 1
    
    return 0


async def run_full_mode(agent_name: str, room_name: Optional[str] = None, verbose: bool = False):
    """Run agent in full audio mode via LiveKit"""
    logging.info(f"Starting full audio mode for agent: {agent_name}")
    
    try:
        agent_runner = AgentRunner(agent_name, room_name, verbose=verbose)
        await agent_runner.run()
    except KeyboardInterrupt:
        logging.info("Full mode interrupted by user")
    except Exception as e:
        logging.error(f"Error in full mode: {e}")
        return 1
    
    return 0


def main():
    """Main entry point - synchronous wrapper for async code"""
    return asyncio.run(async_main())

async def async_main():
    """Async main entry point"""
    args = parse_args()
    setup_logging(args.verbose)
    
    logging.info(f"Starting CLI tool for agent: {args.agent_name}")
    logging.info(f"Mode: {args.mode}")
    
    try:
        if args.mode == "text":
            return await run_text_mode(args.agent_name, args.verbose)
        else:  # full mode
            return await run_full_mode(args.agent_name, args.room_name, args.verbose)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)