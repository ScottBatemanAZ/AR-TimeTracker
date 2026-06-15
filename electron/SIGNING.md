# Code signing the desktop installer

The release pipeline is **wired for Azure Trusted Signing** (a.k.a. *Azure Artifact
Signing*) but signing is **off until you add the repo secrets**. With no secrets,
builds are unsigned exactly as today — Windows SmartScreen warns on first run.
Adding the secrets flips signing on automatically (no code change), which gives
the installer **instant SmartScreen trust** (no warning).

Why Azure Trusted Signing and not a traditional cert: it's ~**$9.99/month**,
cloud-based (no hardware USB token), and integrates with GitHub Actions. A
traditional OV cert (~$200–400/yr) now legally requires a hardware token or paid
cloud HSM — awkward for CI. An EV cert (~$400–700/yr) gives instant trust but
also needs a token. Azure is the cheapest path that removes the SmartScreen
warning for a CI-based release.

## One-time setup

1. **Check eligibility.** Azure Trusted Signing is available to organizations in
   the US/Canada with a **3+ year verifiable business history** (and EU/UK orgs),
   or via an **individual** validation path (US/Canada). Confirm whether
   *Azazel's Razer LLC* qualifies, or use the individual path.
2. **Create the Azure resources** (Azure Portal):
   - A **Trusted Signing account** (note its **name** and its **endpoint** URI,
     e.g. `https://wus2.codesigning.azure.net/`).
   - Complete **identity validation** (takes a few days for the CA to verify).
   - A **Certificate Profile** of type **Public Trust** (note its **name**).
     The profile's certificate **Common Name (CN)** becomes the publisher name.
3. **Create a service principal** (an App Registration) and grant it the
   **Trusted Signing Certificate Profile Signer** role on the Trusted Signing
   account. Record its **tenant ID**, **client ID**, and a **client secret**.
4. **Add GitHub repo secrets** (Settings → Secrets and variables → Actions):

   | Secret | Value |
   |---|---|
   | `AZURE_TENANT_ID` | Service-principal directory (tenant) ID |
   | `AZURE_CLIENT_ID` | Service-principal application (client) ID |
   | `AZURE_CLIENT_SECRET` | Service-principal client secret |
   | `AZURE_ENDPOINT` | Trusted Signing account endpoint URI |
   | `AZURE_CODE_SIGNING_NAME` | Trusted Signing **account** name |
   | `AZURE_CERT_PROFILE_NAME` | Certificate **profile** name |
   | `AZURE_PUBLISHER_NAME` | Certificate CN / publisher display name |

5. **Cut a release** (`git tag vX.Y.Z && git push origin vX.Y.Z`). The
   `build-installer` job picks up the secrets and signs automatically.
   `electron-builder.config.js` logs `Azure Trusted Signing ENABLED` when it sees
   them.

## How the gating works

`electron/electron-builder.config.js` only adds `win.azureSignOptions` when the
`AZURE_*` env vars are present. The CI `build-installer` step passes the secrets
through as env (empty strings until you create them), so:

- **No secrets** → unsigned build, identical to today.
- **Secrets present** → signed installer + Electron app, instant SmartScreen trust.

Local signed builds (rarely needed) work too — set the same env vars in your
shell before `npm run dist`.

## Verifying a signed build

```powershell
Get-AuthenticodeSignature ".\AR-TimeTracker-Desktop-Setup-vX.Y.Z.exe" | Format-List
# Status should be 'Valid'; SignerCertificate should show the publisher.
```

## Follow-ups (optional, not yet wired)

- **Sign the bundled server binary too.** electron-builder signs the Electron app
  and installer, but not the PyInstaller `resources/server/AR-TimeTracker.exe`.
  Windows Defender occasionally flags unsigned PyInstaller bootloaders. To sign it,
  run `Invoke-TrustedSigning` (or `signtool`) on the staged binary in
  `scripts/build-server.js` (or a CI step) after PyInstaller and before
  electron-builder bundles it — gated on the same secrets.
- The standalone `AR-TimeTracker-vX.Y.Z.exe` (the non-Electron EXE built by the
  `build-exe` job) is also unsigned; the same signing call could be added there.
