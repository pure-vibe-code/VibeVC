<div align="center">
  
# VibeVC
</div>

<br>

<div align="center">
<img width="521" height="406" alt="s2" src="https://github.com/user-attachments/assets/7af064ce-4d07-49d9-a367-507351694ec4" />
</div>


<br>



VibeVC is a lightweight, offline-only, and highly resilient local version control system designed for developers who need simple, reliable snapshots without the complexity of distributed systems or online hosting. It prioritizes speed, simplicity, and recoverability.


---

## ✨ Core Current Features (VibeVC v1.2)

<br>

| Feature               | Description                                                                                                                                                               | CLI Command                                | Safety & Architecture                                                                                                    |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Instant Initialization** | Set up a repository in any folder instantly. Creates a hidden `.vibevc` directory for isolated storage.                                                                   | `vibe init`                                 | The `.vibevc` folder is hidden for a clean workspace and is automatically ignored during commits.                         |
| **Versioned Snapshots**    | Create full, timestamped snapshots of your project. Supports optional semantic versioning (e.g., `v1.1`, `beta-2`).                                                     | `vibe commit -m "Msg" -v "v1.1"`            | Each snapshot is a complete copy of project files, making manual recovery simple even if the script fails.               |
| **Granular Status Check**  | Compare the current working directory against the latest snapshot. Reports Modified, New, and Deleted files.                                                           | `vibe status`                               | Uses MD5 hashing for accurate file-level change detection.                                                                |
| **History Logging**        | View a concise history of all committed snapshots, including version tag, timestamp, and commit message.                                                               | `vibe log`                                  | Fetches data from a plain-text `manifest.json` for speed and readability.                                                 |
| **Safe Restoration**       | Revert the working directory back to any committed version. Prevents overwriting uncommitted changes unless forced.                                                    | `vibe restore <version>`<br>`vibe restore <version> --force` | Protects users by blocking accidental overwrites without explicit `--force`.                                              |
| **Intuitive Diffing**      | Generate a unified text diff between the current state and any committed version (defaults to latest). Detects binary changes via hashing.                              | `vibe diff <version>`                       | Supports unified diffs for text and binary-change detection.                                                              |

---

## 📦 Installation

VibeVC is a single Python script.

### **Prerequisites**
- Python **3.x** installed

### **Steps**

1. Download `vibevc.py`
2. Place it inside your project folder
3. Run it using:

```bash
python vibevc.py <command>
