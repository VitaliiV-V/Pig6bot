# Telegram Channel Protection Bot

A Telegram bot designed to protect and moderate channels. It provides message filtering, user banning, whitelist management, logging functionality, AI moderation, and advanced channel security.

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
- AI moderation system
- Real-time message analysis and moderation assistance
- Unified configuration system
- Live configuration editing through Telegram
- Distributed logging system
- Personality mode support
- Docker infrastructure
- Service-based architecture


# Pig-6

Pig-6 is the next generation of the Telegram channel protection system.

This is not just an update.

It is a new architecture.

Svynya-5 was completely redesigned and transformed into a new generation protection system with improved stability, scalability, and intelligence.

The external behavior remains familiar.

Internally, the system has been rebuilt.


# Architecture

Pig-6 uses a service-based architecture.

The system is divided into specialized services:

- Pig-6
    - Main protection and moderation system

- Pig-6 AI
    - AI moderation
    - Message analysis
    - Intelligent responses
    - Context processing

- Pig-6 Logs
    - Distributed logging system
    - Event tracking
    - Independent log processing

- Pig-6 Judgment Day
    - Decision-making system
    - Advanced protection control


# AI Moderation

Pig-6 includes an AI moderation system.

Features:

- Real-time message analysis
- AI-powered moderation assistance
- Smart responses
- Context-aware decisions
- Automated content evaluation


# Unified Configuration System

All bot settings are managed through a unified configuration system.

Features:

- Centralized configuration
- Live configuration editing from Telegram
- Dynamic settings updates
- Easier administration


# Distributed Logging System

Logging is separated from the main bot.

Features:

- Independent logging service
- Better reliability
- Moderation event tracking
- Separate processing and storage


# Personality Mode

Pig-6 supports AI personality modes.

Current personality:

Platnitsa HSE

The AI can operate with a configured style and behavior during interactions.


# Docker Infrastructure

Pig-6 supports Docker-based deployment.

Benefits:

- Predictable deployment
- Easier updates
- Isolated services
- Better scalability


# UUID Protection System

Pig-6 includes a UUID-based message verification system.

Administrators can protect their messages using a unique identifier signature.

After registration, the system can verify whether messages really belong to trusted administrators.

If protection is not enabled, administrator messages may receive:

⚠️ Unsafe message

This is not a restriction.

It is a way to quickly understand whether a message source can be trusted.


# How to enable UUID protection

1. Create a new channel.
2. Add Pig-6 to the channel.
3. Make sure the channel contains only:
    - one administrator
    - the bot
4. Send:

protect

5. Wait for confirmation.

After successful registration, the channel will be added to the trusted sources list.


# Whitelist System

The whitelist system allows administrators to manually control who can interact with the channel.

Available modes:

- off
- admins
- admins_only
- manual

The whitelist system has been improved in Pig-6.

The manual mode is now stricter to provide better security and control.


# Anonymous Message Protection

Pig-6 includes improved anonymous message detection.

Changes:

- Fixed incorrect anonymous message processing
- Better administrator verification
- Improved message source checking


# Markov Text Generator

The bot includes a Markov-chain-based generator trained on parsed2.json.

## How it works

- Uses n-gram model (n=1 and n=2 chains)
- Trained on stored admin messages
- Generates probabilistic text based on context
- Applies temperature-based variation control


# Commands

## Admin commands

### Enable full blocking mode

/blockall


### Enable smart moderation mode

/smart


### Disable protection system

/disable


### Ban user

/ban <username>

or reply to a message in channel:

/ban


### Unban user

/unban <username>


### Set whitelist mode

/setwhitelistsmode <mode>


Available modes:

- off
- admins
- admins_only
- manual


### Add to whitelist

/add <name>


### Remove from whitelist

/del <name>


### Reject request

/reject


# User commands

### Register channel request

/reg <channel_name>


# Requirements

- Python 3.10+
- python-telegram-bot library
- python-dotenv library
- Docker (recommended)
- Properly configured Telegram bot token
- Bot must be admin in the target channel


# Deployment

Install dependencies:

pip install -r requirements.txt


Configure environment:

BOT_TOKEN=your_token_here


Run:

python main.py


# Updates

## Pig-6 Evolution

New generation features:

- AI moderation
- Unified configuration
- Live configuration editing
- Distributed logging
- Personality system
- Docker infrastructure
- Service-based architecture


## Security Improvements

- Stricter whitelist behavior
- Improved anonymous message handling
- UUID-based administrator verification
- Better protection against message spoofing
