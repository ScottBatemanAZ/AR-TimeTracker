# Claude Code Setup — Azazel's Razer Time Tracker

## 1. Install Git for Windows (required)
Download from https://git-scm.com/downloads/win and install with default options.
Make sure "Add Git to PATH" is checked (it is by default).

## 2. Install Claude Code
Open PowerShell (no admin required) and run:

    irm https://claude.ai/install.ps1 | iex

Close and reopen PowerShell when done. Verify with:

    claude --version

If "claude is not recognized", add it to PATH manually:

    [Environment]::SetEnvironmentVariable("PATH", "$env:PATH;$env:USERPROFILE\.local\bin", [EnvironmentVariableTarget]::User)

Then restart PowerShell and try again.

## 3. Authenticate
Run claude from any directory. A browser window opens automatically — log in with your
Claude Pro or Max account. One-time only; token is saved locally.

## 4. Run health check

    claude doctor

## 5. Start a session on the time tracker

    cd D:\timetracker
    claude

That's it. Claude Code will read CLAUDE.md automatically and have full project context.

---

## Notes
- No WSL required — native Windows with Git Bash is fine for this project
- No Node.js required for the native install method above
- The project itself runs via Python (launch.bat / server.py) — no JS build step
- Claude Code can edit index.html directly without the patch.py workaround
