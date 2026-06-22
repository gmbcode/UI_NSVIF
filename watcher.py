import os
import urllib.request
import subprocess
import sys

# Configuration
TAILWIND_EXE = "tailwindcss.exe"
DOWNLOAD_URL = "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe"


def download_tailwind():
    print("Tailwind CSS standalone CLI not found locally.")
    print(
        "Downloading the latest Windows release from GitHub... (This might take a minute depending on your internet connection)")

    try:
        # Fetches the executable and saves it locally as 'tailwindcss.exe'
        urllib.request.urlretrieve(DOWNLOAD_URL, TAILWIND_EXE)
        print("Download complete!")
    except Exception as e:
        print(f"Failed to download Tailwind CLI. Ensure you have an internet connection. Error: {e}")
        sys.exit(1)


def run_watcher():
    print("\nStarting the Tailwind watcher...")

    # The command we established earlier
    command = [
        TAILWIND_EXE,
        "-i", "./static/css/input.css",
        "-o", "./static/css/main.css",
        "--watch"
    ]

    try:
        # subprocess.run will execute the command and stream the output directly to the terminal
        subprocess.run(command)
    except KeyboardInterrupt:
        # Handles the user pressing Ctrl+C gracefully without throwing a massive Python error block
        print("\nWatcher stopped.")
    except Exception as e:
        print(f"\nAn error occurred while trying to run the watcher: {e}")


if __name__ == "__main__":
    # Step 1: Check if the executable is missing
    if not os.path.exists(TAILWIND_EXE):
        download_tailwind()
    else:
        print("Tailwind CSS executable found.")

    # Step 2: Run the watcher
    run_watcher()