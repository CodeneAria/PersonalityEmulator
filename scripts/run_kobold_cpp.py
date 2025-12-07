"""Minimal runner for koboldcpp.

Behavior (simplified per user request):
- If `kobold_cpp/koboldcpp` does not exist, download the official release.
- Spawn `./koboldcpp` in the `kobold_cpp` directory and do not wait.
"""
from __future__ import annotations

import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path


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

    # Spawn the process in the kobold_cpp directory and don't wait for it.
    popen = subprocess.Popen(["./koboldcpp"], cwd=str(kd),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    print(f"Spawned process PID: {popen.pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
