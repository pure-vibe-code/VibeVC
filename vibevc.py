import os
import shutil
import json
import argparse
import hashlib
import difflib
from datetime import datetime
from pathlib import Path

# --- Configuration ---
REPO_DIR_NAME = ".vibevc"
MANIFEST_FILE = "manifest.json"
SNAPSHOTS_DIR = "snapshots"
IGNORE_PATTERNS = {REPO_DIR_NAME, "__pycache__", ".git", ".DS_Store", "venv", ".idea", ".vscode"}

class VibeVC:
    def __init__(self, root_path="."):
        self.root = Path(root_path).resolve()
        self.repo_path = self.root / REPO_DIR_NAME
        self.snapshots_path = self.repo_path / SNAPSHOTS_DIR
        self.manifest_path = self.repo_path / MANIFEST_FILE

    def _get_files(self, directory):
        """Recursively list all files in directory, excluding ignored ones."""
        file_list = []
        for root, dirs, files in os.walk(directory):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
            
            for file in files:
                if file in IGNORE_PATTERNS:
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.root)
                file_list.append(str(rel_path)) # Store as string for JSON serialization
        return sorted(file_list)

    def _hash_file(self, filepath):
        """Generate MD5 hash of a file for precise change detection."""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            return None

    def _load_manifest(self):
        if not self.manifest_path.exists():
            return []
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("(!) Error: Manifest file is corrupted.")
            return []

    def _save_manifest(self, data):
        with open(self.manifest_path, 'w') as f:
            json.dump(data, f, indent=4)

    def _get_commit_by_tag(self, tag):
        """Finds a commit by its version tag."""
        manifest = self._load_manifest()
        for entry in manifest:
            # Use .get('version') to safely access the key, returning None if missing.
            # This handles old, timestamp-only commits gracefully.
            if entry.get('version') == tag:
                return entry
        return None

    def init(self):
        """Initialize the repository."""
        if self.repo_path.exists():
            print("(!) Repository already exists here.")
            return
        
        self.repo_path.mkdir()
        self.snapshots_path.mkdir()
        self._save_manifest([])
        
        # Hide the folder on Windows
        if os.name == 'nt':
            try:
                os.system(f'attrib +h "{self.repo_path}"')
            except:
                pass 
                
        print(f"✅ VibeVC initialized in {self.root}")

    def commit(self, message, version_tag=None):
        """Create a snapshot of the current state."""
        if not self.repo_path.exists():
            print("(!) No repository found. Run 'init' first.")
            return

        # 1. Generate ID and Version Tag
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # If no tag provided, use the ID (old behavior). 
        # If tag provided, ensure it's unique.
        if version_tag:
            if self._get_commit_by_tag(version_tag):
                print(f"(!) Error: Version '{version_tag}' already exists. Pick a new number.")
                return
        else:
            version_tag = unique_id

        # 2. Prepare Snapshot Folder
        snapshot_folder = self.snapshots_path / version_tag
        snapshot_folder.mkdir()

        files = self._get_files(self.root)
        file_tracking = {} # Dictionary to store file: hash mappings

        # 3. Copy files and track hashes
        print(f"📦 Packaging version {version_tag}...")
        for file_rel_path in files:
            src = self.root / file_rel_path
            dst = snapshot_folder / file_rel_path
            
            # Calculate hash for accurate tracking
            file_hash = self._hash_file(src)
            file_tracking[file_rel_path] = file_hash
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 4. Update Manifest with detailed file tracking
        manifest = self._load_manifest()
        manifest.append({
            "version": version_tag,
            "id": unique_id,
            "timestamp": timestamp,
            "message": message,
            "file_map": file_tracking  # Now we know exactly what looked like what
        })
        self._save_manifest(manifest)

        print(f"✅ Snapshot saved: [{version_tag}] {message}")

    def log(self):
        """Show commit history."""
        if not self.repo_path.exists():
            print("(!) No repository found.")
            return

        manifest = self._load_manifest()
        if not manifest:
            print("No snapshots found.")
            return

        print("\n=== VibeVC History ===")
        for entry in reversed(manifest):
            # Safely get version, default to the 'id' (timestamp) for old commits
            version_display = entry.get('version', entry.get('id', 'N/A'))
            
            print(f"Version: {version_display}")
            print(f"Date:    {entry['timestamp']}")
            print(f"Message: {entry['message']}")
            print(f"Files:   {len(entry.get('file_map', []))}")
            print("-" * 30)

    def status(self):
        """Check for modified files compared to latest version."""
        if not self.repo_path.exists():
            print("not initialized")
            return

        manifest = self._load_manifest()
        if not manifest:
            print("No commits yet.")
            return

        last_commit = manifest[-1]
        last_file_map = last_commit.get('file_map', {})
        
        current_files = self._get_files(self.root)
        
        modified = []
        new_files = []
        deleted = []

        # Check existing and new
        for f in current_files:
            if f not in last_file_map:
                new_files.append(f)
            else:
                curr_hash = self._hash_file(self.root / f)
                if curr_hash != last_file_map[f]:
                    modified.append(f)

        # Check deleted
        for f in last_file_map:
            if f not in current_files:
                deleted.append(f)

        if not (modified or new_files or deleted):
            print("✨ Working directory clean")
            return

        print(f"On version: {last_commit['version']}")
        if modified:
            print("\nChanged files:")
            for f in modified: print(f"  M {f}")
        if new_files:
            print("\nNew files:")
            for f in new_files: print(f"  + {f}")
        if deleted:
            print("\nDeleted files:")
            for f in deleted: print(f"  - {f}")

    def restore(self, version_tag, force=False):
        """Restore a specific version."""
        if not self.repo_path.exists():
            return

        target_commit = self._get_commit_by_tag(version_tag)
        if not target_commit:
            print(f"(!) Version {version_tag} not found.")
            return

        target_snapshot = self.snapshots_path / version_tag

        # Safety Check
        if not force:
            # Re-use status logic briefly to check for changes
            manifest = self._load_manifest()
            if manifest:
                last_commit = manifest[-1]
                last_file_map = last_commit.get('file_map', {})
                current_files = self._get_files(self.root)
                is_dirty = False
                
                for f in current_files:
                    if f not in last_file_map or self._hash_file(self.root / f) != last_file_map[f]:
                        is_dirty = True
                        break
                
                if is_dirty:
                    print("(!) Uncommitted changes detected.")
                    print("    Use '--force' to overwrite.")
                    return

        print(f"Restoring version {version_tag}...")
        
        # 1. Wipe current directory
        for item in self.root.iterdir():
            if item.name == REPO_DIR_NAME: continue
            if item.is_dir(): shutil.rmtree(item)
            else: item.unlink()

        # 2. Copy back
        # We walk the snapshot dir directly to ensure we get the actual files stored
        snapshot_files_raw = []
        for root, dirs, files in os.walk(target_snapshot):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(target_snapshot)
                snapshot_files_raw.append(rel_path)

        for file_rel in snapshot_files_raw:
            src = target_snapshot / file_rel
            dst = self.root / file_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        print(f"✅ Restored to {version_tag}")

    def diff(self, version_tag=None):
        """Show text diffs."""
        if not self.repo_path.exists(): return

        manifest = self._load_manifest()
        if not manifest: return

        if not version_tag:
            version_tag = manifest[-1]['version']

        snapshot_dir = self.snapshots_path / version_tag
        if not snapshot_dir.exists():
            print(f"(!) Version {version_tag} not found.")
            return

        print(f"Diffing against {version_tag}...\n")
        
        current_files = set(self._get_files(self.root))
        # Get files present in that snapshot
        snapshot_files_iter = []
        for root, dirs, files in os.walk(snapshot_dir):
            for file in files:
                rel = Path(root).relative_to(snapshot_dir) / file
                snapshot_files_iter.append(str(rel))
        snapshot_files = set(snapshot_files_iter)
        
        all_files = sorted(current_files.union(snapshot_files))
        
        for file in all_files:
            curr_path = self.root / file
            snap_path = snapshot_dir / file
            
            if file in current_files and file in snapshot_files:
                # Calculate hashes first to see if we even need to diff
                if self._hash_file(curr_path) == self._hash_file(snap_path):
                    continue

                try:
                    with open(curr_path, 'r', encoding='utf-8') as f1, \
                         open(snap_path, 'r', encoding='utf-8') as f2:
                        diff = list(difflib.unified_diff(
                            f2.readlines(), f1.readlines(), 
                            fromfile=f"{version_tag}/{file}", 
                            tofile=f"Current/{file}"
                        ))
                        if diff: print("".join(diff))
                except:
                    print(f"Binary file {file} differs")
            
            elif file in current_files:
                print(f"+ {file} (New)")
            elif file in snapshot_files:
                print(f"- {file} (Deleted)")

# --- CLI Entry Point ---

def main():
    parser = argparse.ArgumentParser(description="VibeVC: Simple Local Version Control")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init
    subparsers.add_parser("init", help="Initialize repository")

    # Status
    subparsers.add_parser("status", help="Show changed files")

    # Commit
    commit_parser = subparsers.add_parser("commit", help="Save snapshot")
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")
    commit_parser.add_argument("-v", "--version", help="Version tag (e.g., v1.0). Optional.")

    # Log
    subparsers.add_parser("log", help="Show history")

    # Restore
    restore_parser = subparsers.add_parser("restore", help="Restore a version")
    restore_parser.add_argument("version", help="Version tag to restore")
    restore_parser.add_argument("--force", action="store_true", help="Overwrite changes")

    # Diff
    diff_parser = subparsers.add_parser("diff", help="Show changes")
    diff_parser.add_argument("version", nargs="?", help="Version to diff against")

    args = parser.parse_args()
    vc = VibeVC(os.getcwd())

    if args.command == "init": vc.init()
    elif args.command == "status": vc.status()
    elif args.command == "commit": vc.commit(args.message, args.version)
    elif args.command == "log": vc.log()
    elif args.command == "restore": vc.restore(args.version, args.force)
    elif args.command == "diff": vc.diff(args.version)
    else: parser.print_help()

if __name__ == "__main__":
    main()