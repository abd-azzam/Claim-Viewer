# Word integration

This release uses a native COM ribbon and embedded WebView2 pane. The old developer/shared-folder activation route and writing assistance are retired. Users do not need My Add-ins, a catalog share or Python.

Install through setup or **Settings > Word Add-in > Install Word add-in**. Save/close Word, approve the administrator prompt and start Word normally. Its **Claim Viewer** tab has Insert citation, Add bibliography, Refresh and Citation style. Save a document before opening its pane.

Search by title, author or year and select a source. Add page numbers if needed, then choose **Insert citation**. Word formats the field using its current citation style. To set a different style, expand **Style and bibliography** and apply it once. Use **Add bibliography** at the place in the document where it belongs. Each new citation refreshes the existing bibliography.

The pane also supports narrative citations. Their author text is plain text outside the Word field. APSA is included alongside Word styles. Its installer adapts the locally installed Chicago renderer without redistributing Microsoft files.

## Setup internals

1. `tools/prepare-word-addin.py` generates this account's local token and TLS certificate. Legacy manifest generation remains for compatibility; the native pane does not need catalog activation.
2. `install-web-addin.ps1` protects credentials, trusts the localhost certificate for this account, configures the login service/data folder and installs the account's APSA style.
3. `install-native-ribbon.ps1` installs COM and WebView2 assemblies/loaders with administrator approval, and installs the machine APSA style.
4. `install-ribbon.ps1` registers the current path for both Word bitnesses, removes stale Claim Viewer version registrations and sets the account's always-enable preference.

The service listens only at `127.0.0.1:38491`. The token stays in the native host. Requests require authentication and are bound to the saved document hosting the pane. Setup does not alter macro security, firewall rules or document sharing.

Repair by closing Word, selecting **Repair installation** in Settings and approving the Windows prompt. Setup restarts the citation service after it registers the ribbon. Inspect `installation-error.txt`, `ribbon-install-result.json` or `service-startup.log` on failure. Never distribute service configuration, generated manifests, TLS certificates/private keys, catalog configuration or disabled-entry backups. Staging excludes them.

Uninstall removes Claim Viewer registrations, styles, startup/preference entries and legacy account registration where present. Writing documents and library data remain. See the main README for requirements, backups and release build instructions.
