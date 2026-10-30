import SwiftUI

struct ContentView: View {
    @StateObject private var state = AppState()
    @State private var newKey = ""
    @State private var newValue = ""

    var body: some View {
        NavigationSplitView {
            List(StoreID.allCases, selection: $state.store) { s in
                VStack(alignment: .leading) {
                    Text(s.title)
                    Text(s.subtitle).font(.caption).foregroundStyle(.secondary)
                }
                .opacity(s.implemented ? 1 : 0.45)
                .tag(s)
            }
            .navigationTitle("Stores")
        } detail: {
            VStack(spacing: 0) {
                HStack {
                    TextField("Search keys", text: $state.search)
                        .textFieldStyle(.roundedBorder)
                    Button("Refresh") { Task { await state.refresh() } }
                    Button("Add") {
                        newKey = ""
                        newValue = ""
                        state.showEditor = true
                    }
                    .disabled(!state.store.implemented)
                    Button("Delete", role: .destructive) { Task { await state.deleteSelected() } }
                        .disabled(state.selected == nil)
                    Button("Open editor") { state.openEditor() }
                    SettingsLink { Image(systemName: "gearshape") }
                }
                .padding(8)

                if state.store.implemented {
                    if state.filtered.isEmpty {
                        ContentUnavailableView(
                            "No secrets yet",
                            systemImage: "key.slash",
                            description: Text("Click Add, or from Terminal: agent-keyring set <key> --scope \(state.store == .local ? "local" : "shared")")
                        )
                    } else {
                        List(state.filtered, selection: $state.selected) { row in
                            Text(row.name).tag(row.name)
                        }
                        .onChange(of: state.selected) { _, _ in state.revealed = nil }
                    }

                    Divider()
                    GroupBox("Selected") {
                        if let sel = state.selected {
                            VStack(alignment: .leading, spacing: 8) {
                                Text(sel).font(.headline)
                                if let revealed = state.revealed {
                                    Text(revealed).textSelection(.enabled).font(.system(.body, design: .monospaced))
                                    Button("Copy (clears in 30s)") { state.copyRevealed() }
                                } else {
                                    Button("Reveal (requires Touch ID / password)") {
                                        Task { await state.reveal(sel) }
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        } else {
                            Text("Select a secret to reveal it. Values are never shown in the list.")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(8)
                } else {
                    ContentUnavailableView(
                        "Planned backend",
                        systemImage: "hammer",
                        description: Text("This store will plug in behind the same SecretBackend contract. Secrets are never stored in the app itself.")
                    )
                }

                Divider()
                HStack {
                    if state.isBusy { ProgressView().controlSize(.small) }
                    Text(state.status).font(.caption).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(6)
            }
        }
        .sheet(isPresented: $state.showEditor) {
            VStack(alignment: .leading, spacing: 12) {
                Text(state.editingKey.isEmpty ? "Add secret" : "Edit secret").font(.headline)
                TextField("Key name", text: $newKey)
                SecureField("Value", text: $newValue)
                Text("Shared edits add a new Secret Manager version; old versions stay readable until destroyed.")
                    .font(.caption).foregroundStyle(.secondary)
                HStack {
                    Spacer()
                    Button("Cancel") { state.showEditor = false }
                    Button("Save") { Task { await state.save(key: newKey, value: newValue) } }
                        .disabled(newKey.isEmpty || newValue.isEmpty)
                        .keyboardShortcut(.defaultAction)
                }
            }
            .padding()
            .frame(width: 420)
        }
        .task { await state.refresh() }
        .onChange(of: state.store) { _, _ in Task { await state.refresh() } }
    }
}

@main
struct AgentKeyringApp: App {
    var body: some Scene {
        WindowGroup("Agent Keyring") {
            ContentView()
                .frame(minWidth: 760, minHeight: 460)
        }
        Settings {
            SettingsView()
        }
    }
}
