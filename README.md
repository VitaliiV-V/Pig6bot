# Pig-6

Pig-6 (Свинья-6) is a suite of cooperating **Telegram bots** built with
`python-telegram-bot` that together form a channel protection, moderation,
identity-verification and assistant system. It is designed around a single
primary channel (the "Main Channel") whose integrity, admin list and
content are actively monitored and defended, plus a set of satellite
channels that can opt in to the same protection.

> **Note:** All in-bot user-facing text is in Russian, since the project
> was built for a Russian-speaking community. This README is in English
> for documentation purposes.

## Overview

Pig-6 is not a single bot but **five separate Telegram applications**,
each authenticated with its own bot token, that share a common
`config.json` state file and a common code base (`bot/`, `config/`,
`economy/`, `AI/`):

| Bot | Entry point | Token env var | Purpose |
|---|---|---|---|
| Main / Protection bot | `censor.py`, `channel.py`, `commands.py`, `panel.py`, `protection.py`, `tools.py` | `TOKEN` | Core moderation, admin panel, channel protection |
| Judgment Day bot | `jday.py` | `JUDGMENT_DAY_TOKEN` | Emergency lockdown / mass-deletion protocol |
| Logs bot | `logs.py` | `LOGS_TOKEN` | Forwards every post in the main channel to subscribed users |
| Pig-6 Certificates bot | `Pig6Cert.py` | `CERT_TOKEN` | Cryptographic message signing/verification service |
| Jarvis AI bot | `AI.py`, `AI/jarvis.py` | `AI_TOKEN` | Gemini-powered conversational assistant with voice/text admin commands |

All bots read/write the same `config.json` via `config/config.py`, so
state (moderation mode, whitelist, users, keys, etc.) is shared across
processes.

## Features

### Channel identity protection (`bot/protection.py`)
- Verifies that posts signed with a given `author_signature` (the channel
  post's admin signature) actually belong to the registered owner, a
  "super user", or a "protected" (registered) channel — by comparing it
  against a rotating **name + UUID** pair.
- The UUID is a short string of invisible Unicode variation-selector
  characters (`U+E0100`–`U+E01EF`) appended to the channel/admin title.
  After every legitimate post, the title is rotated to a fresh UUID, so a
  captured/forged signature can only be replayed once before it becomes
  invalid — a lightweight anti-impersonation / anti-replay mechanism.
- Impersonation attempts (title present without the correct current UUID)
  result in immediate deletion of the offending post.
- Channels with only one human admin + the bot can request protection
  (`protect` command in-chat); the request is approved/rejected by the
  owner or root users via an inline keyboard. `unprotect` removes
  protection.

### Pig-6 Certificates (`Pig6Cert.py`)
- Lets registered ("signed") users generate an **Ed25519 keypair**
  (`/start` in the Cert bot).
- Users can sign arbitrary text via an inline query; the bot attaches a
  cryptographic signature and a verification link (`WEB_SITE/check?...`
  or `WEB_SITE/shadow?...` for shadow-role users) to the posted message.
- `bot/protection.py`'s `check_signed_user` extracts the signature/user
  id from the message's link entity and verifies it against the stored
  public key, then maps the signer to a role (`root` / `sudo` / `user`,
  optionally `shadow`) as configured in `config.json["signed_users"]`.
- `/reg <channel name>` lets a user request that a channel be linked to
  their signed identity; owner/root users approve or decline via inline
  buttons.

### Content moderation (`bot/censor.py`)
- `ban_messages` mode can be `off`, `manual` (filtered) or `all`
  (delete everything).
- Manual filtering normalizes text through a leetspeak/character-mapping
  dictionary (`dict.json`) before checking it against a list of banned
  substrings/words in `config.json["banned"]`.
- Simple **anti-flood protection**: if 10+ messages arrive within 5
  seconds, the channel is automatically switched to full lockdown
  (`blockall`) and the recent burst of messages is purged.
- Per-user bans (`banned_users`) and per-GIF bans (`bad_gifs`) are
  enforced on every incoming post.
- A whitelist system (`white_lists_mode`: `off` / `admins` / `manual`)
  can restrict who is allowed to post at all.

### Judgment Day protocol (`tools.EXCOMMUNICADO`, `jday.py`)
- An emergency "lockdown" mode. When triggered (by the owner, a root
  user, or the Jarvis voice command), the main channel is put into
  maximum-security mode and a countdown/announcement sequence runs.
- The dedicated Judgment Day bot (`jday.py`) then deletes **any** message
  in any chat it's added to unless it contains the current secret
  confirmation code (`config.json["Judgment Day Code"]`), which rotates
  every time it's used.
- A protected channel/user can be permanently marked `EXCOMMUNICADO`,
  revoking their protection and blacklisting them.

### Admin control panel (`bot/panel.py`)
- An inline-keyboard dashboard (`/panel`-style entry point via
  `showpanel`) restricted to root users/owner, exposing:
  - Toggle moderation on/off (`blockall` / `disable`).
  - Toggle Judgment Day mode.
  - Browse and manage **Protected users** (mute, EXCOMMUNICADO).
  - Browse **Super users**.
  - Browse and manage **Signed users** (change role, revoke a linked
    channel, toggle "shadow" visibility per channel).

### Logging (`logs.py`)
- Any user can `/start` the Logs bot to subscribe; while
  `config.json["logs_mode"] == "on"`, every post in the main channel is
  forwarded to all subscribers.

### Jarvis AI assistant (`AI.py`, `AI/jarvis.py`)
- Wraps the Google Gemini API (`google-genai`) with a persistent chat
  session and a configurable `base_prompt`.
- Responds when a message mentions "jarvis"/"джарвис" (or is a reply to
  the bot), and runs the same moderation/protection pipeline as the
  main bot on every message it sees.
- A designated "master" user can issue natural-language admin commands
  in Russian (e.g. *"джарвис забань ..."*, *"джарвис включи логи"*,
  *"джарвис судный день"*) to ban/unban users, change the base prompt,
  toggle logging, switch moderation mode, manage the whitelist, or
  trigger/cancel Judgment Day — without touching the panel.

### Economy (`economy/pig6economy.py`)
- A small SQLite-backed token economy (`pig6economy.db`) tracking user
  balances, peer-to-peer transactions, a redeemable-code system, and a
  simple code market with price/volume history — used to gate or reward
  access within the community.

## Configuration

### Environment variables (`.env`, loaded by `bot/settings.py`)

| Variable | Description |
|---|---|
| `TOKEN` | Main/protection bot token |
| `JUDGMENT_DAY_TOKEN` | Judgment Day bot token |
| `LOGS_TOKEN` | Logs bot token |
| `CERT_TOKEN` | Pig-6 Certificates bot token |
| `AI_TOKEN` | Jarvis AI bot token |
| `GEMINI_API_KEY` | Google Gemini API key used by Jarvis |
| `OWNER_ID` | Telegram user ID of the project owner |
| `OWNER_USERNAME` | Owner's @username, shown in some prompts |
| `MAIN_CHANNEL_ID` | ID of the protected main channel |
| `PERSONAL_CHANNEL_ID` | ID of the owner's personal signed channel |
| `WEB_SITE` | Base URL used to build certificate verification links |

### `config.json`
Created automatically on first run by `config/config.py` with sensible
defaults, and then read/written by every bot. Beyond the defaults shown
below, the codebase reads and expects a number of additional keys that
are populated over time through normal use (root/super/protected/signed
user lists, current mode, rotating UUIDs and codes, etc.):

```json
{
  "ban_messages": 0,
  "banned": [],
  "banned_users": [],
  "OWNER_NAMEs": [],
  "white_lists_mode": "off",
  "white_list": [],
  "anon_enable": 0
}
```

Other keys used throughout the code that should exist in a complete
config: `root_users`, `alpha_users`, `protected_users`, `signed_users`,
`owner_name`, `uuid`, `mode`, `Judgment Day Code`, `bad_gifs`, `logs`,
`logs_mode`, `base_prompt`, `AI mode`.

### `dict.json`
A character-normalization map used by the censor to catch
leetspeak/lookalike-character evasion before matching against the
banned-word list.

## Project structure

```
bot/
  censor.py       # word-filtering, flood protection, message pipeline
  channel.py       # channel-post entry point, routing to protection/censor
  commands.py       # private-message admin commands
  panel.py          # inline-keyboard admin control panel
  protection.py      # identity verification, certificates, Judgment Day trigger
  settings.py        # environment variable loading
  tools.py           # ban/unban, blockall/disable, EXCOMMUNICADO, judgment-day toggling
AI/
  jarvis.py           # Gemini chat wrapper
config/
  config.py          # config.json load/save
economy/
  pig6economy.py     # SQLite token economy
AI.py                # Jarvis bot entry point
jday.py              # Judgment Day bot entry point
logs.py              # Logs bot entry point
Pig6Cert.py          # Pig-6 Certificates bot entry point (key generation, signing)
```

## Setup

1. Install dependencies:
   ```bash
   pip install python-telegram-bot python-dotenv cryptography google-genai
   ```
2. Create a `.env` file in the project root with all variables listed
   above.
3. Ensure `dict.json` exists alongside the bots (used by the censor).
4. Run each bot process independently, e.g.:
   ```bash
   python channel.py   # or whichever file wires up the main bot's handlers
   python jday.py
   python logs.py
   python Pig6Cert.py
   python AI.py
   ```
   Each bot polls independently with its own token and shares state
   through `config.json` / `pig6economy.db`.

## Security notes

- The invisible-Unicode UUID rotation and Ed25519 certificate signing
  are the two mechanisms this project relies on to distinguish a
  legitimate admin/channel from an impersonator — both should be
  reviewed carefully before production use, since they are custom,
  unaudited implementations rather than standard, widely-reviewed
  protocols.
- `config.json` and the `keys/private/` directory contain sensitive
  material (banned-user lists, rotating secret codes, private signing
  keys) and should never be committed to version control or exposed
  publicly.
- The Judgment Day protocol is a destructive, irreversible-by-design
  operation (mass deletion / blacklisting) — access to trigger it should
  be tightly restricted to trusted root users.

## License

No license specified.