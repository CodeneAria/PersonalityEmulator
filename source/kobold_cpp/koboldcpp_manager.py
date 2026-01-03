"""KoboldCpp Manager module.

This module provides KoboldCppManager class for managing KoboldCpp processes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import shutil
import stat
import subprocess
import pty
import urllib.request
from typing import Tuple

from config.communcation_settings import (
    KOBOLDCPP_PATH,
    KOBOLDCPP_EXE_FILE,
    KOBOLDCPP_DOWNLOAD_URL,
)

from config.person_settings import (
    KOBOLD_CPP_SIGNATURE,
    STORY_SETTINGS_PATH,
    KOBOLD_CPP_CONFIG_FILE_PATH
)

STORY_SETTINGS_ABSOLUTE_PATH = str(Path(
    STORY_SETTINGS_PATH).resolve())


class KoboldCppManager:
    """Manager class for KoboldCpp process.

    This class handles downloading, configuring, and starting KoboldCpp.
    """

    def __init__(self):
        """Initialize KoboldCppManager."""
        self.kobold_dir = self._get_kobold_dir()
        self.exe_path = self.kobold_dir / KOBOLDCPP_EXE_FILE
        self.cfg_path = self._get_config_path()

    def _get_kobold_dir(self) -> Path:
        """Get the KoboldCpp directory path.

        Returns:
            Path to the KoboldCpp directory.
        """
        return Path(__file__).resolve().parents[2] / KOBOLDCPP_PATH

    def _get_config_path(self) -> Path:
        """Get the KoboldCpp config file path.

        Returns:
            Absolute path to the config file.
        """
        cfg_path = Path(KOBOLD_CPP_CONFIG_FILE_PATH)
        if not cfg_path.is_absolute():
            cfg_path = Path(__file__).resolve().parents[2] / cfg_path
        return cfg_path.resolve()

    def _download_file(self, url: str, dest_dir: Path) -> Path:
        """Download a file from URL to destination directory.

        Args:
            url: URL to download from.
            dest_dir: Destination directory.

        Returns:
            Path to the downloaded file.

        Raises:
            RuntimeError: If download fails.
        """
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

    def _download_koboldcpp(self) -> Path:
        """Download the official koboldcpp Linux x64 binary.

        Tries `curl` first, falls back to Python downloader.

        Returns:
            Path to the downloaded executable.

        Raises:
            RuntimeError: If download fails.
        """
        url = KOBOLDCPP_DOWNLOAD_URL
        self.kobold_dir.mkdir(parents=True, exist_ok=True)
        out = self.kobold_dir / KOBOLDCPP_EXE_FILE
        curl = shutil.which("curl")
        if curl:
            cmd = [curl, "-fLo", str(out.name), url]
            print(
                f"Running curl to download koboldcpp: {' '.join(cmd)} (cwd={self.kobold_dir})")
            try:
                subprocess.run(cmd, cwd=str(self.kobold_dir), check=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"curl download failed: {e}")
        else:
            downloaded = self._download_file(url, self.kobold_dir)
            out = downloaded

        # Ensure the downloaded file is renamed to the configured executable name
        final = self.kobold_dir / KOBOLDCPP_EXE_FILE
        try:
            if out.name != final.name:
                if final.exists():
                    final.unlink()
                try:
                    out.replace(final)
                except Exception:
                    shutil.move(str(out), str(final))

            # Ensure executable bit set
            final.chmod(final.stat().st_mode | stat.S_IXUSR)
        except Exception:
            try:
                subprocess.run(["chmod", "+x", str(final)], check=False)
            except Exception:
                pass

        return final

    def ensure_koboldcpp_exists(self) -> bool:
        """Ensure KoboldCpp executable exists, download if necessary.

        Returns:
            True if executable exists or was successfully downloaded, False otherwise.
        """
        if not self.exe_path.exists():
            print("`koboldcpp` not found in `kobold_cpp` — downloading official release.")
            try:
                self.exe_path = self._download_koboldcpp()
            except Exception as e:
                print(f"Failed to download koboldcpp: {e}", file=sys.stderr)
                return False

        # Ensure executable bit
        try:
            self.exe_path.chmod(self.exe_path.stat().st_mode | stat.S_IXUSR)
        except Exception:
            try:
                subprocess.run(
                    ["chmod", "+x", str(self.exe_path)], check=False)
            except Exception:
                pass

        return True

    def set_story_to_koboldcpp_config(self) -> None:
        """
        Set the story settings path in the KoboldCpp config file.
        """
        with open(KOBOLD_CPP_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config_data = f.read()

        config_data = config_data.replace(
            "\"preloadstory\": null,", f"\"preloadstory\": \"{STORY_SETTINGS_ABSOLUTE_PATH}\",")

        with open(KOBOLD_CPP_CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(config_data)

    def reset_story_to_koboldcpp_config(self) -> None:
        """
        Reset the story settings path in the KoboldCpp config file to null.
        """
        with open(KOBOLD_CPP_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config_data = f.read()

        config_data = config_data.replace(
            f"\"preloadstory\": \"{STORY_SETTINGS_ABSOLUTE_PATH}\",", "\"preloadstory\": null,")

        with open(KOBOLD_CPP_CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(config_data)

    def wait_for_koboldcpp_startup(self, master_fd: int) -> None:
        try:
            dup_fd = os.dup(master_fd)
            try:
                with os.fdopen(dup_fd, mode='r', buffering=1) as r:
                    for line in r:
                        try:
                            print(f"{KOBOLD_CPP_SIGNATURE} {line}", end="")

                            if "Please connect to custom endpoint at " in line:
                                break
                        except Exception:
                            # Keep trying until we find the marker or EOF
                            continue
            except Exception as e:
                print(
                    f"[KoboldCppManager] Monitoring read error: {e}", file=sys.stderr)

        except Exception as e:
            print(
                f"[KoboldCppManager] Failed to duplicate master fd: {e}", file=sys.stderr)

    def start_koboldcpp(self) -> Tuple[int, int, subprocess.Popen]:
        """Start KoboldCpp process with PTY.

        Returns:
            Tuple of (master_fd, slave_fd, process).

        Raises:
            RuntimeError: If KoboldCpp cannot be started.
        """
        if not self.ensure_koboldcpp_exists():
            raise RuntimeError("KoboldCpp executable not available")

        master_fd, slave_fd = pty.openpty()

        self.set_story_to_koboldcpp_config()

        koboldcpp_process = subprocess.Popen(
            [f"./{KOBOLDCPP_EXE_FILE}", "--config", str(self.cfg_path)],
            cwd=str(self.kobold_dir),
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self.wait_for_koboldcpp_startup(master_fd)

        self.reset_story_to_koboldcpp_config()

        return master_fd, slave_fd, koboldcpp_process
