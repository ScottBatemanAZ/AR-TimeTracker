// electron-builder configuration.
//
// Code signing (Azure Trusted Signing / "Azure Artifact Signing") activates ONLY
// when the AZURE_* env vars are present — set as GitHub Actions secrets (see
// SIGNING.md). With no secrets, builds are unsigned exactly as before, so local
// `npm run dist` and the current CI release keep working untouched.
//
// When signing is on, electron-builder signs the Electron app executable and the
// NSIS installer. (The bundled PyInstaller server binary in resources/server/ is
// not signed by this step — see SIGNING.md "Follow-ups".)

const signing =
  process.env.AZURE_TENANT_ID &&
  process.env.AZURE_CODE_SIGNING_NAME &&
  process.env.AZURE_CERT_PROFILE_NAME &&
  process.env.AZURE_ENDPOINT;

if (signing) {
  console.log('electron-builder: Azure Trusted Signing ENABLED (AZURE_* env present)');
} else {
  console.log('electron-builder: signing disabled (no AZURE_* env) — building unsigned');
}

/** @type {import('electron-builder').Configuration} */
module.exports = {
  appId: 'com.azazelsrazer.timetracker',
  productName: "Azazel's Razer Time Tracker",
  directories: {
    output: 'dist',
    buildResources: 'build',
  },
  files: ['main.js', 'preload.js', 'assets/**', 'package.json'],
  extraResources: [{ from: 'resources/server', to: 'server' }],
  win: {
    target: 'nsis',
    icon: 'build/icon.ico',
    // Present only when signing is configured. electron-builder reads the Azure
    // service-principal credentials (AZURE_TENANT_ID / AZURE_CLIENT_ID /
    // AZURE_CLIENT_SECRET) from the environment automatically.
    ...(signing
      ? {
          azureSignOptions: {
            publisherName: process.env.AZURE_PUBLISHER_NAME,
            endpoint: process.env.AZURE_ENDPOINT,
            codeSigningAccountName: process.env.AZURE_CODE_SIGNING_NAME,
            certificateProfileName: process.env.AZURE_CERT_PROFILE_NAME,
          },
        }
      : {}),
  },
  nsis: {
    oneClick: false,
    perMachine: false,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    shortcutName: 'AR Time Tracker',
    installerIcon: 'build/icon.ico',
    uninstallerIcon: 'build/icon.ico',
  },
};
