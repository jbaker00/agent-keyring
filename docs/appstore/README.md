# App Store Connect pack — Agent Keyring (macOS)

All copy lives in `en-US/*.txt`, sized to Apple's limits and ready to paste or push via the ASC API. URLs assume the GitHub Pages files in `~/code/jbaker00.github.io` are published (`agent-keyring.html`, `-support`, `-privacy`).

| Field | Limit | Ours | Source |
| --- | --- | --- | --- |
| Name | 30 | 13 | `name.txt` |
| Subtitle | 30 | 21 | `subtitle.txt` |
| Promotional text | 170 | 152 | `promotional_text.txt` (editable anytime, no review) |
| Keywords | 100 | 94 | `keywords.txt` (comma, no spaces) |
| Description | 4000 | ~1570 | `description.txt` |
| Support / Marketing / Privacy URLs | — | jbaker00.github.io pages | `*_url.txt` |

## Settings to choose in App Store Connect

- **Price:** Free. **Primary category:** Developer Tools. **Secondary:** Utilities.
- **Age rating:** expect 4+ (no objectionable content, no ads, no tracking — answer all content questions None/No; `advertising=false`).
- **App Privacy (web UI only, must click Publish):** Data Not Collected. The app has no server/analytics; preferences are local pointers. This matches `agent-keyring-privacy.html`.
- **Export compliance:** set `ITSAppUsesNonExemptEncryption=false` (standard OS crypto only).
- **Availability:** all territories **except China mainland** (standing policy; declare CHN `available:false` via API). Verify after approval — Ready for Sale without an availability record means live nowhere.
- **Marketing levers:** promotional text (update per release without review), subtitle + keywords above (name/subtitle/keywords are the indexed fields — "api key", "keychain", "secrets", "developer" carry the search weight), marketing URL set at first submission (it locks once the version is live), screenshots showing: store list with named keys, Touch ID reveal, Settings pointing at own gcloud. No promotional IAP image (there are no IAPs).

## ⚠️ Submission gate — read before submitting

The current app is **unsandboxed** (`app-sandbox=false`) because it spawns the user's `gcloud`/`aws`/`az`/`oci` CLIs. The Mac App Store requires sandboxing, so **this build cannot be submitted to the Mac App Store as-is**. Options, in order:

1. **Developer ID + notarized DMG** (DevSweep model): distribute via GitHub Releases + the marketing page; the copy above works unchanged as release/marketing text.
2. **Re-architect for the Store:** direct Secret Manager/AWS/Azure/OCI REST + OAuth per cloud, no subprocesses, sandboxed entitlements (keychain-access-groups), then submit using this pack.

Decision needed from the owner before anyone burns a review cycle.

## Who presses Submit

Standing rule: automation prepares everything (archive, upload, metadata, screenshots, availability); **the owner clicks Add for Review / Submit**. Post-approval, run a go-live check: version READY_FOR_SALE **and** availability record with >0 territories **and** price schedule **and** storefront lookup hits.
