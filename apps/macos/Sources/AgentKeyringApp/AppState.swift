import AppKit
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var store: StoreID = .local
    @Published var rows: [SecretRow] = []
    @Published var selected: String?
    @Published var revealed: String?
    @Published var search = ""
    @Published var status = ""
    @Published var showEditor = false
    @Published var editingKey = ""
    @Published var isBusy = false

    private let local = KeychainStore()
    private let shared = GCloudStore()

    init() {
        let d = UserDefaults.standard.string(forKey: "defaultStore") ?? ""
        if d == "shared" { store = .shared }
    }

    var clipboardSeconds: Int {
        let v = UserDefaults.standard.integer(forKey: "clipboardSeconds")
        return v > 0 ? v : 30
    }

    var filtered: [SecretRow] {
        search.isEmpty ? rows : rows.filter { $0.name.localizedCaseInsensitiveContains(search) }
    }

    func refresh() async {
        isBusy = true
        defer { isBusy = false }
        revealed = nil
        do {
            let names: [String]
            switch store {
            case .local: names = try local.list()
            case .shared: names = try await shared.list()
            default: names = []
            }
            rows = names.map(SecretRow.init)
            status = "\(names.count) secret(s) in \(store.title)"
        } catch {
            rows = []
            status = "Error: \(error.localizedDescription)"
        }
    }

    func reveal(_ key: String) async {
        guard await authenticate(reason: "Reveal a secret in Agent Keyring") else {
            status = "Authentication cancelled — secret not revealed."
            return
        }
        do {
            let v: String?
            switch store {
            case .local: v = try local.get(key)
            case .shared: v = try await shared.get(key)
            default: v = nil
            }
            revealed = v
            status = v == nil ? "Not found." : "Revealed \(key) (this session only)"
        } catch {
            status = "Error: \(error.localizedDescription)"
        }
    }

    func copyRevealed() {
        guard let revealed else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(revealed, forType: .string)
        status = "Copied. Clipboard clears in \(clipboardSeconds) seconds."
        let snapshot = revealed
        Task {
            try? await Task.sleep(nanoseconds: UInt64(clipboardSeconds) * 1_000_000_000)
            if NSPasteboard.general.string(forType: .string) == snapshot {
                NSPasteboard.general.clearContents()
            }
        }
    }

    func save(key: String, value: String) async {
        do {
            switch store {
            case .local: try local.set(key, value)
            case .shared: try await shared.set(key, value)
            default: break
            }
            showEditor = false
            await refresh()
        } catch {
            status = "Error: \(error.localizedDescription)"
        }
    }

    func deleteSelected() async {
        guard let selected else { return }
        do {
            switch store {
            case .local: _ = try local.delete(selected)
            case .shared: _ = try await shared.delete(selected)
            default: break
            }
            self.selected = nil
            revealed = nil
            await refresh()
        } catch {
            status = "Error: \(error.localizedDescription)"
        }
    }

    func openEditor() {
        switch store {
        case .local:
            let url = URL(fileURLWithPath: "/System/Applications/Utilities/Keychain Access.app")
            NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration())
        case .shared:
            let project = ProcessInfo.processInfo.environment["AGENT_KEYRING_GCP_PROJECT"] ?? ""
            var url = "https://console.cloud.google.com/security/secret-manager"
            if !project.isEmpty { url += "?project=\(project)" }
            if let u = URL(string: url) { NSWorkspace.shared.open(u) }
        default:
            status = "This backend is planned — no editor yet."
        }
    }
}
