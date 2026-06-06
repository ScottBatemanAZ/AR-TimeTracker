# Verifying Your Download

This page explains how to confirm your download is authentic and hasn't been
tampered with, and why Windows may warn you about the EXE.

---

## Why Does Windows Show a Warning?

When you run `AR-TimeTracker.exe`, Windows SmartScreen may display:

> **"Windows protected your PC"**

This happens because the EXE is not yet **code-signed** — a process where a
certificate authority (like DigiCert or Sectigo) charges ~$500/year to verify
the publisher's identity and attach a digital signature.

**This does not mean the file is dangerous.** It means Windows doesn't
recognize the publisher yet. The full source code is publicly available at:

> https://github.com/ScottBatemanAZ/AR-TimeTracker

You can inspect every line before running it.

### To run the EXE anyway:
1. Click **"More info"** in the SmartScreen dialog
2. Click **"Run anyway"**

---

## Verifying the SHA-256 Checksum

Every release includes a `checksums-vX.X.X.txt` file. The checksum lets you
confirm that the file you downloaded is byte-for-byte identical to what was
built and published — proof it wasn't modified in transit.

### Windows (PowerShell or Command Prompt)

```powershell
certutil -hashfile AR-TimeTracker-vX.X.X.exe SHA256
```

```powershell
certutil -hashfile AR-TimeTracker-vX.X.X.zip SHA256
```

Compare the output to the matching line in `checksums-vX.X.X.txt`.
They must match exactly.

### macOS / Linux

```bash
sha256sum AR-TimeTracker-vX.X.X.zip
```

---

## Checking on VirusTotal

Each release is scanned on [VirusTotal](https://www.virustotal.com) before
publishing. The scan link is included in the release notes when available.

You can also scan the file yourself:
1. Go to https://www.virustotal.com
2. Click **"Choose file"** and select the downloaded EXE or ZIP
3. Review the results

> **Note on false positives:** PyInstaller-packaged executables are sometimes
> flagged by a small number of AV engines as generic "suspicious" behavior.
> This is a known false-positive pattern with self-contained Python EXEs —
> not an indication of malware. If the checksum matches and the majority of
> AV engines show clean, the file is safe.

---

## Building From Source

If you prefer to build the EXE yourself rather than trusting a pre-built
binary, the full instructions are in the [README](README.md). You need:
- Python 3.10+
- `pip install pyinstaller`
- `pyinstaller AR-TimeTracker.spec`

The resulting EXE in `dist/` is functionally identical to the one in the
release — built from the same source code.

---

## Questions or Concerns

Open an issue at https://github.com/ScottBatemanAZ/AR-TimeTracker/issues
