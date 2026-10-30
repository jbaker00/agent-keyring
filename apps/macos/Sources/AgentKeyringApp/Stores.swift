import Foundation
import LocalAuthentication
import Security

enum StoreID: String, CaseIterable, Identifiable {
    case local, shared, onepassword, lastpass, chrome
    var id: String { rawValue }
    var title: String {
        switch self {
        case .local: return "Local Keychain"
        case .shared: return "Google Cloud (your project)"
        case .onepassword: return "1Password"
        case .lastpass: return "LastPass"
        case .chrome: return "Chrome Passwords"
        }
    }
    var implemented: Bool { self == .local || self == .shared }
    var subtitle: String {
        switch self {
        case .local: return "This Mac only"
        case .shared: return "Synced via your gcloud login"
        default: return "Planned backend"
        }
    }
}

struct SecretRow: Identifiable, Hashable {
    let name: String
    var id: String { name }
}

enum StoreError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        if case .message(let m) = self { return m }
        return "Unknown error"
    }
}

/// Local store: native Security framework query filtered to our service.
/// This is why the app can list local secrets while the Python `keyring`
/// API cannot — same login keychain, same items the CLI writes.
final class KeychainStore {
    static let service = "agent-keyring"

    private func baseQuery(_ account: String? = nil) -> [String: Any] {
        var q: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
        ]
        if let account { q[kSecAttrAccount as String] = account }
        return q
    }

    func list() throws -> [String] {
        var q = baseQuery()
        q[kSecReturnAttributes as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitAll
        var out: CFTypeRef?
        let st = SecItemCopyMatching(q as CFDictionary, &out)
        if st == errSecItemNotFound { return [] }
        guard st == errSecSuccess, let items = out as? [[String: Any]] else {
            throw StoreError.message("Keychain list failed (OSStatus \(st))")
        }
        return items.compactMap { $0[kSecAttrAccount as String] as? String }.sorted()
    }

    func get(_ key: String) throws -> String? {
        var q = baseQuery(key)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        let st = SecItemCopyMatching(q as CFDictionary, &out)
        if st == errSecItemNotFound { return nil }
        guard st == errSecSuccess, let d = out as? Data else {
            throw StoreError.message("Keychain read failed (OSStatus \(st))")
        }
        return String(data: d, encoding: .utf8)
    }

    func set(_ key: String, _ value: String) throws {
        let data = Data(value.utf8)
        let attrs: [String: Any] = [kSecValueData as String: data]
        let st = SecItemUpdate(baseQuery(key) as CFDictionary, attrs as CFDictionary)
        if st == errSecSuccess { return }
        if st == errSecItemNotFound {
            var q = baseQuery(key)
            q[kSecValueData as String] = data
            let add = SecItemAdd(q as CFDictionary, nil)
            guard add == errSecSuccess else {
                throw StoreError.message("Keychain write failed (OSStatus \(add))")
            }
            return
        }
        throw StoreError.message("Keychain update failed (OSStatus \(st))")
    }

    func delete(_ key: String) throws -> Bool {
        let st = SecItemDelete(baseQuery(key) as CFDictionary)
        if st == errSecItemNotFound { return false }
        guard st == errSecSuccess else {
            throw StoreError.message("Keychain delete failed (OSStatus \(st))")
        }
        return true
    }
}

/// Shared store: thin wrapper over the user's own `gcloud` login.
/// No credentials are embedded or read by the app — gcloud owns auth,
/// IAM on the user's own project decides access. Secret values are
/// passed on stdin, never argv, so they stay out of process listings.
final class GCloudStore {
    func gcloudPath() -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let candidates = [
            "\(home)/google-cloud-sdk/bin/gcloud",
            "/opt/homebrew/bin/gcloud", "/usr/local/bin/gcloud",
        ]
        if let found = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) {
            return found
        }
        return "/usr/bin/gcloud"
    }

    @discardableResult
    func run(_ args: [String], stdin: String? = nil) async throws -> String {
        try await withCheckedThrowingContinuation { cont in
            let p = Process()
            p.executableURL = URL(fileURLWithPath: gcloudPath())
            p.arguments = args
            let outPipe = Pipe(), errPipe = Pipe()
            p.standardOutput = outPipe
            p.standardError = errPipe
            if stdin != nil { p.standardInput = Pipe() }
            p.terminationHandler = { proc in
                let out = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                let err = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                if proc.terminationStatus == 0 {
                    cont.resume(returning: out)
                } else {
                    cont.resume(throwing: StoreError.message(err.trimmingCharacters(in: .whitespacesAndNewlines)))
                }
            }
            do {
                try p.run()
                if let stdin, let pipe = p.standardInput as? Pipe {
                    pipe.fileHandleForWriting.write(Data(stdin.utf8))
                    try? pipe.fileHandleForWriting.close()
                }
            } catch {
                cont.resume(throwing: StoreError.message("Could not launch gcloud: \(error.localizedDescription)"))
            }
        }
    }

    func list() async throws -> [String] {
        let out = try await run(["secrets", "list", "--format=value(name)"])
        return out.split(separator: "\n").map(String.init).sorted()
    }

    func get(_ key: String) async throws -> String? {
        do {
            var v = try await run(["secrets", "versions", "access", "latest", "--secret=\(key)"])
            if v.hasSuffix("\n") { v.removeLast() }
            return v
        } catch StoreError.message(let m) where m.contains("NOT_FOUND") {
            return nil
        }
    }

    func set(_ key: String, _ value: String) async throws {
        let exists = (try? await get(key)) != nil
        if !exists {
            _ = try await run(["secrets", "create", key, "--replication-policy=automatic"])
        }
        _ = try await run(["secrets", "versions", "add", key, "--data-file=-"], stdin: value)
    }

    @discardableResult
    func delete(_ key: String) async throws -> Bool {
        do {
            _ = try await run(["secrets", "delete", key, "--quiet"])
            return true
        } catch StoreError.message(let m) where m.contains("NOT_FOUND") {
            return false
        }
    }
}

/// Require device-owner auth (Touch ID / Mac password) before reveal/copy.
func authenticate(reason: String) async -> Bool {
    let ctx = LAContext()
    var err: NSError?
    guard ctx.canEvaluatePolicy(.deviceOwnerAuthentication, error: &err) else { return false }
    return (try? await ctx.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason)) ?? false
}
