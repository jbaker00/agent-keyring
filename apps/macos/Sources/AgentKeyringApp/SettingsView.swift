import SwiftUI

/// All settings persist in UserDefaults — never secrets, only pointers
/// (paths, project, keychain service) and preferences.
struct SettingsView: View {
    @AppStorage("gcloudPath") private var gcloudPath = ""
    @AppStorage("gcpProject") private var gcpProject = ""
    @AppStorage("localService") private var localService = "agent-keyring"
    @AppStorage("clipboardSeconds") private var clipboardSeconds = 30
    @AppStorage("defaultStore") private var defaultStore = "local"

    @State private var detected = ""
    @State private var testResult = ""
    private let shared = GCloudStore()

    var body: some View {
        Form {
            Section("Google Cloud") {
                TextField("gcloud path (blank = auto-detect)", text: $gcloudPath)
                    .font(.system(.body, design: .monospaced))
                LabeledContent("Auto-detected") {
                    Text(detected.isEmpty ? "—" : detected)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                }
                TextField("GCP project (blank = gcloud config)", text: $gcpProject)
                    .font(.system(.body, design: .monospaced))
                HStack {
                    Button("Test Google Cloud") { Task { await test() } }
                    Text(testResult).font(.caption).foregroundStyle(.secondary)
                }
                Text("Uses your own gcloud login and project. Nothing is embedded in the app.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Section("Local Keychain") {
                TextField("Keychain service", text: $localService)
                    .font(.system(.body, design: .monospaced))
                Text("Must match the CLI's service (default agent-keyring) or the app and CLI will see different items.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Section("Behaviour") {
                Picker("Open to store", selection: $defaultStore) {
                    Text("Local Keychain").tag("local")
                    Text("Google Cloud").tag("shared")
                }
                Stepper("Clear clipboard after \(clipboardSeconds)s", value: $clipboardSeconds, in: 5...300, step: 5)
            }
        }
        .formStyle(.grouped)
        .frame(width: 520)
        .onAppear { detected = GCloudStore().gcloudPath() ?? "not found — install Google Cloud SDK" }
    }

    private func test() async {
        do {
            let keys = try await shared.list()
            testResult = "OK — \(keys.count) secret(s) visible under your login"
        } catch {
            testResult = "Failed: \(error.localizedDescription)"
        }
    }
}
