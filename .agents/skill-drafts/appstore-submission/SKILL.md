---
name: appstore-submission
description: Prepare and push an Apple app submission — icons, GitHub Pages marketing/privacy/support pages, App Store Connect metadata and marketing fields, and API-vs-web-UI steps — stopping before the final Submit for the owner to press.
---

# App Store Submission (James Baker's pattern)

Use when asked to prepare, market, or submit an iOS/macOS app: app icon, product pages, App Store Connect (ASC) metadata, screenshots, availability, or release marketing. Distilled from the DevSweep/DogTalk/NFS Files releases. DevSweep-style notarized-DMG distribution is the fallback when sandbox rules block the Store.

## Standing rules

- **The owner presses Submit.** Automate everything up to it (build, upload, metadata, screenshots, availability), then stop and report ready. Never create the final review submission unless explicitly told to in that conversation.
- **Never commit secrets.** ASC API keys (`.p8`), passwords, or tokens never go into any repo. Reference keys by path only.
- **No China mainland availability** (ICP/encryption burdens). Declare `CHN available:false`.
- **Verify go-live after approval:** version READY_FOR_SALE *and* an availability record with >0 territories *and* a price schedule *and* public storefront lookup hits. Ready-for-Sale with no availability record means live nowhere.

## 1. Icon

- Generate a 1024×1024 master (readable at 16px, no text, full-bleed). Crop any generated margin to the artwork's squircle, apply rounded-corner alpha (~190px radius at 1024).
- Slice with PIL/sips to the 10 mac sizes (16–512 @1x/@2x) into `Assets.xcassets/AppIcon.appiconset` + `Contents.json`; also `iconutil -c icns` for SwiftPM/manual bundles. Wire `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon` and rebuild; confirm `AppIcon.icns`/`Assets.car` lands in the built `.app`.

## 2. Web pages (GitHub Pages: `~/code/jbaker00.github.io`, flat files, `style.css`)

Create three files matching the house pattern (navbar, hero gradient, feature grid, footer):

- `<app>.html` — hero (icon/emoji, name, one-line value prop, CTA to download/source), a differentiation wedge paragraph, feature cards, compat line (platform · tech · license · no account/ads/tracking). This file doubles as the ASC **marketing URL** — set it at first submission; it locks once a version is live.
- `<app>-support.html` — how to get help (GitHub Issues), common problems with exact fixes, security notes. Doubles as **support URL**.
- `<app>-privacy.html` — what is stored where, what the app accesses, third parties, children, contact. Must match the App Privacy answers. Doubles as **privacy URL**.

Add an index card to `index.html` (icon, 2-sentence pitch, tags, App Info + download buttons). Leave the site repo for the owner to review/commit/push unless told otherwise.

## 3. ASC metadata pack (in the app repo: `docs/appstore/en-US/`)

One `.txt` per field, sized to limits: name ≤30, subtitle ≤30, promotional text ≤170, keywords ≤100 (comma-separated, no spaces — name/subtitle/keywords are the search-indexed fields; promotional text is editable anytime without review), description ≤4000, plus support/marketing/privacy URLs. Add `docs/appstore/README.md` with: price, primary/secondary categories, expected age rating, App Privacy answers, export compliance (`ITSAppUsesNonExemptEncryption=false` unless custom crypto), availability rule (all but CHN), screenshot shot-list, and marketing levers. Count characters programmatically before declaring done.

## 4. Sandbox gate (macOS, check first)

Mac App Store requires the app sandbox. If the app spawns user CLIs or reads arbitrary user files, it is not submittable as-is: stop and present (a) Developer ID signed + notarized DMG via GitHub Releases (marketing copy still applies), or (b) re-architecture (direct REST + OAuth, keychain-access-groups, sandboxed entitlements). Do not burn a review cycle.

## 5. API vs web UI (ASC API with the owner's key, JWT ES256, `aud=appstoreconnect-v1`)

API-able: register bundle ID; archive/export/upload builds (`xcodebuild` + `altool` with the API key; bump build number every upload and verify it inside the archive); PATCH metadata (subtitle, description, keywords, promotional text, copyright, categories); age-rating declaration (include `advertising` — must be true if the app has ads); screenshots (reserve → PUT bytes to the CDN URL with *only* its request headers, never the ASC auth header → commit with md5 checksum); territory availability (declare every territory, CHN false).

Web-UI only — never fight the API for these: creating the app record (API returns 403); App Privacy nutrition label (must click **Publish**, not just save); first-time pricing; review contact phone; the final Submit.

Known locks: description/keywords/URLs/categories lock once a version is READY_FOR_SALE (409 STATE_ERROR) — only promotional text stays editable; changing locked fields means a new version + build + fresh review. `whatsNew` is rejected on a first version and required on later ones.

## 6. Finish

Report: icon set location and build verification, the three page paths + index card, metadata pack path with per-field character counts, sandbox verdict, what was pushed via API vs what remains for the owner in the web UI (privacy Publish, pricing, Submit), and — after approval — the four-part go-live verification result. Use computer use only for the web-UI-only steps when explicitly asked; otherwise hand them over as a checklist.
