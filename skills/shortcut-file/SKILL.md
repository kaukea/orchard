---
name: shortcut-file
description: Read and emit Apple Shortcuts `.shortcut` files (iOS 15+) at the byte level on any platform — the AEA→Apple Archive→WFWorkflow-bplist layering, the action/parameter serialization shapes, and the signing/import reality. Invoke when parsing an exported shortcut, generating a `.shortcut` off-device, or debugging why a generated shortcut is rejected or misbehaves on import.
roles: [development/file-formats]
metadata:
  tags: [apple-shortcuts, shortcut-file, wflow, bplist, aea, apple-archive, signing-import]
  share: github
---

# Apple Shortcuts `.shortcut` file format

The knowledge fastcut compiles against: how a `.shortcut` is layered, how actions and
parameters serialize, and what the phone will and won't accept. Every shape below was
verified byte-level against a real, working exported shortcut and cross-checked against
Apple's own `WFActions` dump (scpl `OutActions.json`) and the ShortcutsBench parameter
catalogue; where sources disagreed, the ground-truth file won.

## Layering

```
.shortcut  =  AEA (Apple Encrypted Archive, signed container)
              └─ payload: LZFSE-compressed Apple Archive (AA)
                  └─ Shortcut.wflow  = the workflow, a binary plist (bplist00)
```

### Layer 1 — AEA wrapper (magic `AEA1`)
| offset | size | field |
|---|---|---|
| 0 | 4 | magic `41 45 41 31` ("AEA1") |
| 4 | 3 | profile ID (LE). **Shortcuts use profile 0** = `hkdf_sha256_hmac_none_ecdsa_p256` → **signed, NOT encrypted** |
| 7 | 1 | scrypt strength (0) |
| 8 | 4 | auth-data length (uint32 LE) |
| 12 | n | auth data = a **bplist** (contact/iCloud-signed → holds `SigningCertificateChain`, 3 DER certs to Apple; other modes use `SigningPublicKey`/`AppleIDValidationRecord`) |
| 12+n | … | ECDSA-P256 signature (DER `30 45 …`), then AEA cluster/HMAC structures (~18 KB of segment HMACs even for a tiny file), then the payload segments |

Because profile 0 is unencrypted, the payload is recoverable with **no key**: find the LZFSE
stream after the auth data and decompress to EOF (`pyliblzfse`). The stream does **not** always
start with `bvx2` — small payloads emit `bvx-` (raw) or `bvxn` (LZVN) with no `bvx2` at all.
**Search for the earliest of `bvx2` / `bvxn` / `bvx-`**; liblzfse decodes all three.

### Layer 2 — Apple Archive (magic `AA01` per entry)
Sequence of entries: `AA01` + uint16 header-size + field list. Field = 3-char key + subtype:
`P` (uint16-len-prefixed string/blob), `1`/`2`/`4`/`8` (uints), `A`/`B` (uint16/uint32 `DAT`
size), `T` (12-byte timespec = u64 sec + u32 nsec). Entry data (`DAT` size) follows the header.
Typical: one dir entry (`TYP1`=D) then `PAT`=`Shortcut.wflow` (`TYP1`=F) with the bplist.

### Layer 3 — Shortcut.wflow (the WFWorkflow plist)
Top-level: `WFWorkflowMinimumClientVersion`, `WFWorkflowClientVersion`, `WFWorkflowIcon`,
`WFWorkflowActions` (the list), `WFWorkflowInputContentItemClasses`, `WFWorkflowTypes`,
`WFWorkflowImportQuestions`, `WFQuickActionSurfaces`, `WFWorkflowNoInputBehavior`, …
Each action: `{WFWorkflowActionIdentifier: "is.workflow.actions.<x>", WFWorkflowActionParameters: {…}}`.

## Parameter serialization shapes
- **Magic-variable reference (attachment):** `{"Value":{"Type":"ActionOutput","OutputUUID":"<source action uuid>","OutputName":"<display name>"},"WFSerializationType":"WFTextTokenAttachment"}`. Named vars: `{"Type":"Variable","VariableName":"Repeat Item"}` (also `Repeat Index`); `Current Date` is `{"Type":"CurrentDate"}`.
- **Text with embedded tokens:** `WFTextTokenString` — `{"string":"a￼b","attachmentsByRange":{"{1, 1}":<attachment Value>}}`. Each token is U+FFFC; ranges are in **UTF-16 code units**.
- **Aggrandizements** (property/format/coercion on a token): `WFPropertyVariableAggrandizement` (`PropertyName`+`PropertyUserInfo`), `WFDateFormatVariableAggrandizement` (`WFDateFormatStyle` `ISO 8601`/`Custom`+`WFDateFormat`), `WFCoercionVariableAggrandizement` (`CoercionItemClass`).
- **Control flow is FLAT** in the action list, linked by a shared `GroupingIdentifier` + `WFControlFlowMode` (0=open, 1=Otherwise, 2=close). Conditionals: `WFCondition` (Is=4, Not=5, Contains=99, DoesNotContain=999, BeginsWith=8, EndsWith=9, GreaterThan=2, GreaterOrEqual=3, LessThan=0, LessOrEqual=1, Between=1003, Any=100, Empty=101); the `WFInput` is **double-wrapped**: `{"Type":"Variable","Variable":<attachment>}`.
- **Value TYPE matters, not just the key.** Number-typed fields (`WFNumberValue`, `WFItemIndex`, `WFItemRangeStart/End`, `WFDelayTime`, `WFNumberActionNumber`) take a plist `<integer>`, **not** a string. A variable in a **number** field serializes as a bare `WFTextTokenAttachment`; a variable in a **text** field (`WFTextInputParameter`, incl. `WFSSHHost/Port/User/Password`) as a `WFTextTokenString` with attachments; a **literal** in a text field is a bare plain string.
  - ⚠ A `WFTextTokenString` **without** `attachmentsByRange` appears in no ground truth — it is an invented shape and a refusal suspect. Emit plain strings for literals.
- **Empty-variable init idiom:** `nothing` then `setvariable` (no `WFInput`).

### Action specifics (exact keys — verified against Apple's dump + ShortcutsBench + a ground-truth file)
- `runsshscript`: `WFSSHHost/WFSSHPort/WFSSHUser/WFSSHPassword` plain strings, `WFSSHAuthenticationType:"Password"`, `WFSSHScript` a WFTextTokenString; output name **"Shell Script Result"** (current iOS; old dumps say "Run Script Over SSH").
- `deletephotos`: single param key `photos` (**not** `WFInput`).
- `filter.photos` (Find Photos): `WFContentItemFilter`, `WFContentItemSortProperty` ("Date Taken","Duration","File Size"…), `WFContentItemSortOrder` ("Oldest First","Longest First"…), `WFContentItemLimitEnabled` (switch), `WFContentItemLimitNumber` (stepper).
- `properties.images` (Get Details of Images): `WFInput` (the image/PHAsset) + `WFContentItemPropertyName`; output **"Details of Images"**. Valid property names: Album, Width, Height, Date Taken, Media Type, Photo Type, Is a Screenshot, Is a Screen Recording, Location, Duration, Frame Rate, Orientation, Camera Make, Camera Model, Metadata Dictionary, Is Favorite, File Size, File Extension, Creation Date, File Path, Last Modified Date, Name.
- File-server locations (`WFFolder`, Save File's service) serialize as device-local bookmarks (`fileProviderDomainID`, `crossDeviceItemID`) — they **cannot be fabricated off-device**; the user must re-pick the location after import.

## Signing / import reality (iOS 15+)
- Unsigned plists are REJECTED on import; the old "untrusted shortcuts" toggle is gone.
- The signature chains to Apple identity certs (contact-signed) or Apple-issued keys — **cannot be forged locally**. `shortcuts sign` exists only on macOS.
- Off-device signing services exist (e.g. HubSign / RoutineHub helpers) but are **unreliable** — a signed-but-wrong envelope or client-version mismatch imports yet fails at runtime. Treat any off-device signing path as a suspect until proven on the target iOS version.

## Gotchas
- `plutil`/`plistlib` choke on the outer file — it is NOT a plist; strip the AEA first. The `bplist00` visible at offset 12 is only the *auth data*.
- LZFSE stream offset varies with auth-data size; **search for the block magic**, never hardcode. The AEA cluster HMAC section (≈18 KB even for tiny payloads) sits between signature and payload — the payload does not start right after the signature.
- Any action whose output is referenced needs a `UUID` param; `attachmentsByRange` ranges are UTF-16 units.

## Sources
0xilis "Reversing Contact Signed Shortcuts" + libshortcutsign; zachary7829 "Shortcuts File
Format"; Apple's `WFActions` dump (scpl `OutActions.json`); ShortcutsBench (EachSheep); The Apple
Wiki "Apple Encrypted Archive" — all reconciled against a real exported shortcut, which wins on
conflict.
