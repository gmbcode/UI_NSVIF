"""
Tailwind CSS Watcher Script.

This script ensures the Tailwind CSS standalone executable is available
locally. If missing, it downloads it. Then, it starts the Tailwind watcher
process to continuously compile CSS during development.
"""

import os
import urllib.request
import subprocess
import sys
from typing import List

# Configuration
TAILWIND_EXE: str = "tailwindcss.exe"
DOWNLOAD_URL: str = (
    "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/"
    "tailwindcss-windows-x64.exe"
)


def download_tailwind() -> None:
    """
    Download the Tailwind CSS standalone CLI for Windows.

    Attempts to fetch the executable from GitHub and save it locally.
    Exits the script if the download fails.
    """
    print("Tailwind CSS standalone CLI not found locally.")
    print(
        "Downloading the latest Windows release from GitHub... "
        "(This might take a minute depending on your internet connection)"
    )

    try:
        # Fetches the executable and saves it locally as 'tailwindcss.exe'
        urllib.request.urlretrieve(DOWNLOAD_URL, TAILWIND_EXE)
        print("Download complete!")
    except Exception as e:
        print(
            f"Failed to download Tailwind CLI. Ensure you have an internet "
            f"connection. Error: {e}"
        )
        sys.exit(1)


def run_watcher() -> None:
    """
    Start the Tailwind CSS watcher process.

    Executes the tailwind CLI to monitor the input CSS file for changes
    and recompile the output CSS file automatically. Gracefully handles
    KeyboardInterrupt for clean exits.
    """
    print("\nStarting the Tailwind watcher...")

    # The command we established earlier
    command: List[str] = [
        TAILWIND_EXE,
        "-i",
        "./static/css/input.css",
        "-o",
        "./static/css/main.css",
        "--watch",
    ]

    try:
        # subprocess.run will execute the command and stream the output directly to the terminal
        subprocess.run(command)
    except KeyboardInterrupt:
        # Handles the user pressing Ctrl+C gracefully without throwing a massive Python error block
        print("\nWatcher stopped.")
    except Exception as e:
        print(f"\nAn error occurred while trying to run the watcher: {e}")


def main() -> None:
    """
    Main entry point for the script.
    Checks for the executable and starts the watcher.
    """
    # Step 1: Check if the executable is missing
    if not os.path.exists(TAILWIND_EXE):
        download_tailwind()
    else:
        print("Tailwind CSS executable found.")

    # Step 2: Run the watcher
    run_watcher()


if __name__ == "__main__":
    main()