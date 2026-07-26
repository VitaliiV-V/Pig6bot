# Telegram Channel Protection Bot

A Telegram bot designed to protect and moderate Telegram channels.

It provides message filtering, user banning, whitelist management, logging functionality, AI moderation, advanced channel security and intelligent protection systems.

Official website:

https://pig6bot.sos.al


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
- UUID-based administrator verification
- Unicode-enhanced protection signatures
- Invisible security identifiers
- AI moderation system
- Real-time message analysis
- Intelligent response system
- Markov text generator
- Unified configuration system
- Live configuration editing through Telegram
- Distributed logging system
- Personality mode support
- Docker infrastructure
- Service-based architecture
- Content protection system
- Protected file handling
- Secure GIF processing
- Extreme Protection mode


# Pig-6

Pig-6 is the next generation of the Telegram channel protection system.

This is not just an update.

It is a new architecture.

Svynya-5 was completely redesigned and transformed into a new generation protection system with improved stability, scalability and intelligence.

The external behavior remains familiar.

Internally, the system has been rebuilt.


# Designed to protect

Pig-6 was created with one main principle:

Security should work quietly.

The system focuses on reliability, verification and intelligent protection without unnecessary complexity.

Created by Hammam Inc.


# Architecture

Pig-6 uses a service-based architecture.

The system is divided into specialized services:


## Pig-6 Core

Main protection and moderation system.

Responsible for:

- message security
- channel control
- administrator verification
- protection logic


## Pig-6 AI

Artificial intelligence subsystem.

Features:

- AI moderation
- message analysis
- context processing
- intelligent responses
- decision assistance


## Pig-6 Logs

Distributed logging system.

Features:

- event tracking
- independent log processing
- security history
- moderation records


## Pig-6 Judgment Day

Advanced decision system.

Responsible for:

- complex protection decisions
- advanced control mechanisms
- security evaluation


## Pig6Guard

Official protection module.

Provides:

- Telegram channel protection
- administrator verification
- security control
- advanced protection modes


# AI Moderation

Pig-6 includes an AI moderation system.

Features:

- Real-time message analysis
- Context-aware decisions
- Automated content evaluation
- Smart responses
- Moderation assistance


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

Pig-6 includes a UUID-based administrator verification system.

Administrators can protect their messages using unique security signatures.

The system verifies whether messages actually belong to trusted administrators.

Protection uses:

- UUID identifiers
- Unicode-based invisible signatures
- Additional validation layers


If protection is not enabled, administrator messages may receive:

⚠️ Unsafe message


This is not a restriction.

It is a way to quickly understand whether a message source can be trusted.


# Extreme Protection

Extreme Protection is the highest security level available in Pig-6.

This mode is available only to:

- system owners
- trusted superusers


Features:

- Advanced Unicode-based identification
- Invisible security signatures
- Additional anti-spoofing protection
- Maximum control mode
- Extended verification rules


Extreme Protection is designed for situations where standard protection is not enough.

Maximum protection.

Minimum visibility.


# Content Protection System

Pig-6 includes additional protection for user-uploaded content.

Features:

- Secure file processing
- Content tracking
- Controlled access
- Administrative approval system
- File removal capability


The system helps prevent unwanted content from being distributed through protected channels.


# Protected GIF System

Pig-6 supports secure GIF handling.

Features:

- Protected GIF downloads
- Controlled access
- Administrator confirmation
- Secure processing flow


Files can be reviewed before becoming available.


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
- Trained on stored administrator messages
- Generates probabilistic text based on context
- Applies temperature-based variation control


# Source Code Security

The Pig-6 source code is no longer publicly available.

The project has moved to a closed-source model.

This decision was made to improve security, protect internal mechanisms and prevent misuse of the system.


# Commands

## Admin commands

/blockall

Enable full blocking mode.


/smart

Enable smart moderation mode.


/disable

Disable protection system.


/ban <username>

Ban user.


/unban <username>

Unban user.


/setwhitelistsmode <mode>

Set whitelist mode.


Available modes:

- off
- admins
- admins_only
- manual


/add <name>

Add user to whitelist.


/del <name>

Remove user from whitelist.


/reject

Reject request.


# User commands

/reg <channel_name>

Register channel request.


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
- Unicode protection
- Extreme Protection
- Content Protection
- Pig6Guard module


## Security Improvements
 
- Stricter whitelist behavior
- Improved anonymous message handling
- UUID administrator verification
- Unicode security signatures
- Better protection against message spoofing
- Advanced content control
- Improved administrator security 
 