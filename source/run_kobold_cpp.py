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
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.communcation_settings import (
    KOBOLDCPP_PATH,
    KOBOLDCPP_EXE_FILE,
    KOBOLDCPP_DOWNLOAD_URL,
    KOBOLDCPP_CONFIG_FILE_PATH,
)
from source.speaker.voice_manager import VoiceManager

cfg_path = Path(KOBOLDCPP_CONFIG_FILE_PATH)
if not cfg_path.is_absolute():
    cfg_path = Path(__file__).resolve().parents[1] / cfg_path
cfg_path = cfg_path.resolve()

KOBOLD_CPP_SIGNATURE = "[KoboldCpp]"


def kobold_dir() -> Path:
    # repo root is one level above the `scripts` directory
    return Path(__file__).resolve().parents[1] / KOBOLDCPP_PATH


def download_file(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urllib.request.urlparse(
        url).path).name or KOBOLDCPP_EXE_FILE
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
    url = KOBOLDCPP_DOWNLOAD_URL
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / KOBOLDCPP_EXE_FILE
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
    exe = kd / KOBOLDCPP_EXE_FILE

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
        [f"./{KOBOLDCPP_EXE_FILE}", "--config", str(cfg_path)],
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
    previous_capture_state = False

    vm = VoiceManager()
    try:
        vm.start()
    except Exception as e:
        print(f"[Runner] Failed to start VoiceManager: {e}", file=sys.stderr)

    try:
        with os.fdopen(master_fd, mode='r', buffering=1) as r:
            for line in r:
                # Writing to stdout may fail (e.g. debugger/pipe closed, I/O errors).
                # Protect the runner from crashing on such errors and exit loop
                # gracefully if writes fail.
                try:
                    print(f"{KOBOLD_CPP_SIGNATURE} {line}", end="")
                except OSError as e:
                    # Log to stderr and stop trying to write to stdout.
                    try:
                        print(
                            f"[Runner] stdout write failed: {e}", file=sys.stderr)
                    except Exception:
                        # If even stderr is not available, silently stop.
                        pass
                    break

                if line.startswith("Input:"):
                    print(f"[Runner] Detected 'Input:' line")
                    capture_state = False
                    captured_text = ""

                    # Clear queues when capture_state becomes False
                    if previous_capture_state and not capture_state:
                        print(
                            f"[Runner] Capture state changed from True to False, clearing queues...")
                        try:
                            vm.request_clear()
                        except Exception as e:
                            print(
                                f"[Runner] Failed to clear queues: {e}", file=sys.stderr)

                elif line.startswith("Output:"):
                    print(f"[Runner] Detected 'Output:' line")
                    capture_state = True

                previous_capture_state = capture_state

                if capture_state:
                    captured_text = line.removeprefix("Output:").strip()
                    print(f"[Runner] Captured text: '{captured_text}'")
                    if captured_text == "":
                        print(f"[Runner] Captured text is empty, skipping")
                        continue

                    texts = captured_text.split('。')
                    # Filter out empty strings
                    texts = [text for text in texts if text.strip() != '']
                    print(f"[Runner] Split into {len(texts)} texts: {texts}")

                    if not texts:
                        print(f"[Runner] No valid texts after split, skipping")
                        continue

                    try:
                        # Queue text for async voice generation and playback
                        print(
                            f"[Runner] Calling vm.generate_voice with texts: {texts}")
                        vm.generate_voice(texts)
                    except Exception as e:
                        print(
                            f"[Runner] VoiceManager error: {e}", file=sys.stderr)

    finally:
        try:
            vm.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
