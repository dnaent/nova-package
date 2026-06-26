import os
import shutil
import subprocess
import zipfile

import magic  # python-magic library


class UploadSecurity:
    def __init__(self, antivirus_config=None, quarantine_dir="/tmp/quarantine"):
        """
        Initializes the upload security scanner.
        antivirus_config (dict): Configuration for the antivirus scanner, e.g., ClamAV socket.
        quarantine_dir (str): Directory to move suspicious files to.
        """
        self.antivirus_config = antivirus_config or {}
        self.quarantine_dir = quarantine_dir
        if not os.path.exists(self.quarantine_dir):
            os.makedirs(self.quarantine_dir)

    async def scan_for_malware(self, file_path: str) -> bool:
        """
        Scans a file for malware using a tool like ClamAV.
        Returns True if malware is detected, False otherwise.
        """
        # This is a conceptual integration with ClamAV.
        # It requires the 'clamscan' command-line tool to be installed.
        print(f"Scanning {file_path} for malware...")
        try:
            result = subprocess.run(['clamscan', '--no-summary', file_path], capture_output=True, text=True)
            if "Infected files: 1" in result.stdout:
                print(f"Malware detected in {file_path}: {result.stdout}")
                await self.quarantine_suspicious_file(file_path)
                return True
            print("No malware detected.")
            return False
        except FileNotFoundError:
            print("ClamAV scanner not found. Skipping malware scan.")
            return False
        except Exception as e:
            print(f"An error occurred during malware scan: {e}")
            return False # Fail safe

    async def check_archive_bomb(self, archive_path: str, max_ratio=10, max_size_gb=1) -> bool:
        """
        Checks for zip bomb characteristics (high compression ratio).
        Returns True if it's likely a zip bomb, False otherwise.
        """
        print(f"Checking {archive_path} for archive bomb characteristics...")
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                total_uncompressed_size = sum(file.file_size for file in zf.infolist())

            compressed_size = os.path.getsize(archive_path)

            if compressed_size == 0:
                return False # Avoid division by zero

            ratio = total_uncompressed_size / compressed_size

            if ratio > max_ratio or total_uncompressed_size > max_size_gb * 1024**3:
                print(f"Potential archive bomb detected. Ratio: {ratio:.2f}, Uncompressed Size: {total_uncompressed_size}")
                return True

            print("Archive bomb check passed.")
            return False
        except zipfile.BadZipFile:
            print("Not a valid zip file.")
            return False # Not a zip bomb if not a zip file

    async def verify_file_type(self, file_data: bytes, claimed_extension: str) -> bool:
        """
        Verifies the actual file type against its claimed extension using libmagic.
        Returns True if the type is valid, False otherwise.
        """
        print(f"Verifying file type for a file claiming to be '{claimed_extension}'...")
        try:
            mime_type = magic.from_buffer(file_data, mime=True)
            # This is a very basic check. A real implementation would have a comprehensive
            # mapping of extensions to allowed MIME types.
            print(f"Detected MIME type: {mime_type}")
            if claimed_extension.lower() in ['.jpg', '.jpeg'] and 'image/jpeg' not in mime_type:
                return False
            if claimed_extension.lower() == '.py' and 'text/' not in mime_type:
                return False
            return True
        except Exception as e:
            print(f"Could not verify file type: {e}")
            return False # Fail safe

    async def scan_for_embedded_scripts(self, file_content: str) -> bool:
        """
        A conceptual check for embedded scripts in non-script files.
        Returns True if suspicious scripts are found.
        """
        # This is a placeholder. A real implementation would be more sophisticated.
        print("Scanning for embedded scripts...")
        if "<script>" in file_content and "</script>" in file_content:
            print("Suspicious <script> tag found in file content.")
            return True
        return False

    async def quarantine_suspicious_file(self, file_path: str):
        """Moves a suspicious file to the quarantine directory."""
        if not os.path.exists(file_path):
            print(f"File {file_path} not found for quarantining.")
            return

        try:
            file_name = os.path.basename(file_path)
            quarantine_path = os.path.join(self.quarantine_dir, file_name)
            shutil.move(file_path, quarantine_path)
            print(f"File {file_path} quarantined to {quarantine_path}")
        except Exception as e:
            print(f"Failed to quarantine file {file_path}: {e}")
