# Disk Cleanup Report

*Generated 2026-06-02 from real `du` data. Read-only analysis — nothing was deleted.*

## Summary

- **Disk:** ~460 GB total, **only ~45 GB free** — cleanup is worth doing.
- **Biggest consumers:** Telegram cache 26G · Steam 20G · `.paperclip` 13G · `node_modules` (all) 12G · Claude Desktop VM bundles 8.3G · Chrome 6.3G · ImaGame 5.9G.
- **Tier 1 (safe to delete, regenerable):** ≈ **30 GB** — caches, build artifacts, duplicate archives, used installers.
- **Tier 2 (review — your call):** ≈ **90+ GB** — app caches, games, old projects, personal media.

---

## Tier 1 — Safe to delete now (regenerable / disposable)

These regenerate automatically or are duplicates/used installers. ~30 GB total.

| Area | Size | Why safe | How to reclaim |
|------|------|----------|----------------|
| `node_modules` (38 dirs under Documents) | **12.0 G** | 100% regenerable from lockfiles | `find ~/Documents -name node_modules -type d -prune -exec rm -rf {} +` then `npm/pnpm install` per project when needed |
| `~/.cache` | 4.9 G | Generic app/build cache | `rm -rf ~/.cache/*` |
| `~/.npm` | 3.9 G | npm download cache | `npm cache clean --force` |
| `~/Library/Caches` — updater leftovers (`*.ShipIt`: todesktop 1.1G, anthropic 672M, notion 292M) | ~2.1 G | Finished app-update staging | safe to delete the `*ShipIt*` dirs |
| `~/Library/Caches/ms-playwright` | 1.5 G | Browser binaries, re-download on demand | `rm -rf ~/Library/Caches/ms-playwright` |
| `~/Library/Caches/Google` (Chrome cache) | 1.5 G | Browser cache | clears itself; safe to delete |
| `~/Library/pnpm` (store) | 1.9 G | pnpm content store | `pnpm store prune` (frees the unreferenced part) |
| Claude Desktop `Cache` + `Code Cache` | ~1.1 G | App caches | safe; app rebuilds them |
| `~/Library/Caches` misc (go-build 146M, pip 91M, Homebrew 89M, node-gyp 62M, claude-cli 294M) | ~0.7 G | Tool caches | `brew cleanup -s`, `pip cache purge`, rest `rm -rf` |
| Downloads: used installers + duplicate archives (`tsetup…dmg` 127M, `V_tishine…rar` 195M, `PLX2.7z` 126M, `PLX3.7z` 49M, `video.zip` 120M) | ~0.6 G | Installers already used / archives of folders you already extracted | move to Trash |
| `Documents/PLX3 2` (Aug 2025) + `PLX3.7z` — older copies of `PLX3` (Jan 2026) | ~0.11 G | Stale duplicates of the current `PLX3` | delete the old `2` + `.7z`, keep `PLX3` |
| `~/.claude/backups` (our skills-cleanup backups) | 0.45 G | Snapshot backups from this session's cleanup | delete once you're happy nothing's missing |

---

## Tier 2 — Review before deleting (large, but maybe wanted)

| Area | Size | Question to ask yourself |
|------|------|--------------------------|
| **Telegram** `Group Containers/…keepcoder.Telegram` | **26 G** | Cached chat media. Clear via Telegram → Settings → Data and Storage → Clear Cache. Re-downloads when you open old chats. **Single biggest win.** |
| **Steam** (App Support 20G + Battle.net 1.5G) | ~21 G | Games. Delete titles you're not playing — re-download to play again. |
| `~/.paperclip/instances` | 13 G | Paperclip tool instance data. Keep if you actively use Paperclip; old instances are prunable. |
| Claude Desktop `vm_bundles` | 8.3 G | VM images for Claude Code VM mode. If you don't use VM mode, removable (re-downloads if you re-enable). |
| **Chrome** `App Support/Google` | 6.3 G | Profile data (history, extensions, local storage). Deleting logs you out / drops unsynced data. |
| `Documents/GitHub/ImaGame` | 5.9 G | Unity/engine project — `Library/` & build dirs regenerate, but `.git`+assets are real. Review what's artifact vs source. |
| Android SDK + emulator (`~/.android` 4.0G + `~/Library/Android` 4.4G) | ~8.4 G | Keep only if doing Android dev. Emulator system-images are huge and re-downloadable. |
| Notion cache (3.5G) · Comet (2.2G) · WhatsApp media (3.2G) | ~8.9 G | App local caches — clearable, re-sync from server. |
| Stale client projects in `Documents/Apps` (e.g. `Sergei` 2G, `VitaliiLev` 1G, `Woiz`, `AntonCalendarDashboard`, finished one-offs) | ~10–15 G | If a project is delivered/dead, archive it off-disk (external/cloud) and remove locally. You know which are done. |
| Downloads personal (`V_tishine_Trackout` 897M music stems, `your_instagram_activity` 731M, `Course_BobAI_free` 481M, `SharedWithImaginus` 316M) | ~2.5 G | Personal — move to cloud/external if you want to keep, else delete. |

---

## Tier 3 — Keep (don't touch)

- **Source code** working trees (everything in Apps/GitHub that isn't `node_modules`/`.next`/`dist`/`build`/`Library`).
- `~/.claude/projects` (1.2 G session history) + config/memory.
- **Personal media:** `Music`, `Movies`, `Pictures`, `.xmind` mind-maps, original recordings.
- Keychains, Preferences, dotfile configs.

---

## Top 5 highest-impact actions (GB freed per unit of risk)

1. **Delete all `node_modules`** → **~12 G**, zero risk (regenerate with install). One command.
2. **Clear Telegram cache** (in-app) → **up to 26 G**, low risk (media re-downloads).
3. **Clear `~/.cache` + `npm cache clean` + pnpm prune + Library caches** → **~14 G**, zero risk.
4. **Trim Steam** — delete unplayed games → **up to ~20 G**, low risk (re-downloadable).
5. **Archive 2–3 finished client projects** off-disk → **~10 G**, low risk if you have them in git/cloud.

Tier 1 alone (#1 + #3 + duplicates) frees **~30 GB** with essentially zero risk.

---

## ⚠️ Caution notes

- **Telegram / WhatsApp cache:** clearing deletes locally cached media; most re-downloads, but anything a sender later deleted may be gone.
- **Chrome profile:** don't delete the whole `Google` folder — only its `Cache`. Removing the profile logs you out and drops unsynced state.
- **`rm -rf node_modules`:** safe only inside projects with a committed lockfile. Don't run it where you can't `install` again.
- **Steam:** deleting = full re-download to play.
- **`vm_bundles` / Android emulator:** large and re-downloadable, but re-download takes time/bandwidth.
- **Always confirm an installer's app is installed** before trashing the `.dmg`.

---

### Footnote on the run
The requested 30-Haiku-agent workflow failed: background worker agents couldn't execute shell commands (`du`/`ls`), so they returned no data (`tool_uses: 0`, all 30 failed the structured-output step after ~18 min). This report was instead built from the same `du` measurements gathered directly during reconnaissance — same data the agents were meant to collect, without the broken fan-out.
