"""Minimal runner for koboldcpp.

Behavior (simplified per user request):
- If `kobold_cpp/koboldcpp` does not exist, download the official release.
- Spawn `./koboldcpp` in the `kobold_cpp` directory and do not wait.
"""
from __future__ import annotations

import shutil
import stat
import subprocess
import os
import sys
import pty
import urllib.request
import select
import time
from pathlib import Path

# Configuration: timeout in seconds before triggering voicevox
IDLE_TIMEOUT = 0.5


def kobold_dir() -> Path:
    # repo root is one level above the `scripts` directory
    return Path(__file__).resolve().parents[1] / "kobold_cpp"


def download_file(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urllib.request.urlparse(url).path).name or "koboldcpp"
    out = dest_dir / filename
    print(f"Downloading {url} -> {out}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        if getattr(resp, "status", 200) >= 400:
            reason = getattr(resp, "reason", "")
            raise RuntimeError(
                f"Download failed: {getattr(resp, 'status', 'ERR')} {reason}")
        with open(out, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    out.chmod(out.stat().st_mode | stat.S_IXUSR)
    return out


def download_koboldcpp_default(dest: Path) -> Path:
    """Download the official koboldcpp Linux x64 binary into `dest`.

    Tries `curl` first, falls back to the Python downloader.
    """
    url = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-linux-x64"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "koboldcpp"
    curl = shutil.which("curl")
    if curl:
        cmd = [curl, "-fLo", str(out.name), url]
        print(
            f"Running curl to download koboldcpp: {' '.join(cmd)} (cwd={dest})")
        try:
            subprocess.run(cmd, cwd=str(dest), check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"curl download failed: {e}")
    else:
        out = download_file(url, dest)
        return out

    try:
        out.chmod(out.stat().st_mode | stat.S_IXUSR)
    except Exception:
        try:
            subprocess.run(["chmod", "+x", str(out)], check=False)
        except Exception:
            pass
    return out


def main() -> int:
    kd = kobold_dir()
    exe = kd / "koboldcpp"

    if not exe.exists():
        print("`koboldcpp` not found in `kobold_cpp` — downloading official release.")
        try:
            exe = download_koboldcpp_default(kd)
        except Exception as e:
            print(f"Failed to download koboldcpp: {e}", file=sys.stderr)
            return 2

    # ensure executable bit
    try:
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    except Exception:
        try:
            subprocess.run(["chmod", "+x", str(exe)], check=False)
        except Exception:
            pass

    master_fd, slave_fd = pty.openpty()

    koboldcpp_process = subprocess.Popen(
        ["./koboldcpp"],
        cwd=str(kd),
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    os.close(slave_fd)

    capture_state = False
    captured_text = ""
    voicevox_script = Path(__file__).resolve(
    ).parent / "voicevox" / "voicevox.py"

    with os.fdopen(master_fd, mode='r', buffering=1) as r:
        for line in r:

            if line.startswith("Please connect to custom endpoint at"):
                print("[KoboldCpp]", line, end="")

            if line.startswith("Input:"):
                capture_state = False
                captured_text = ""

            elif line.startswith("Output:"):
                capture_state = True

            if capture_state:
                captured_text = line.removeprefix("Output:").strip()
                if captured_text == "":
                    continue

                print("[KoboldCpp]", line, end="")

                texts = captured_text.split('。')
                for text in texts:
                    if text == '':
                        continue
                    try:
                        result = subprocess.run(
                            ["python3", str(voicevox_script), "-t",
                             text, "-id", "8"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                    except Exception as e:
                        print(
                            f"[Timeout] Failed to run voicevox: {e}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
