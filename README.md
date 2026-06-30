# Telegram Channel Protection Bot

A Telegram bot designed to protect and moderate channels. It provides message filtering, user banning, whitelist management, and logging functionality.

# Features
- Automatic message filtering and deletion
- User banning and unbanning (via commands and reply)
- Multiple moderation modes:
    - off — no filtering
    - admins — only admins allowed
    - admins_only — strict admin-only mode
    - manual — whitelist-based control
- Whitelist system for allowed users
- Anonymous message blocking
- Message forwarding to a log channel
- Owner-only administrative commands
- UUID-based protection mechanism for ownership validation
- Markov text generator


# Markov text generator

The bot includes a Markov-chain-based generator trained on parsed2.json.

## How it works
- Uses n-gram model (n=1 and n=2 chains)
- Trained on stored admin messages
- Generates probabilistic text based on context
- Applies temperature-based variation control


# Commands
## Admin commands
### Enable full blocking mode
    '/blockall'
### Enable smart moderation mode
    '/smart'
### Disable protection system
    '/disable'
### Ban user
    '/ban <username>'

    or reply to a message in channel
    '/ban'

### Unban user
    '/unban <username>'
### Set whitelist mode
    '/setwhitelistsmode <mode>'

#### Available modes:

- off
- admins
- admins_only
- manual

### Add to whitelist
    '/add <name>'
### Remove from whitelist
    '/del <name>'
### Reject request
    '/reject'

## User commands
### Register channel request
    '/reg <channel_name>'

# Requirements
- Python 3.10+
- python-telegram-bot library
- python-dotenv library
- Properly configured Telegram bot token
- Bot must be admin in the target channel