#!/usr/bin/env python3

import subprocess
import sys
import os


def main():
    """Run tests with proper environment setup."""
    
    # Set PYTHONPATH to include src directory
    env = os.environ.copy()
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{src_path}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = src_path
    
    # Default pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    try:
        # Run pytest
        result = subprocess.run(cmd, env=env, cwd=os.path.dirname(__file__))
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTest execution interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()