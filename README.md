# TGSessionsConverter | VX Edition

<div align="center">
  <img src="https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/Resources/art/icon256.png" alt="Telegram Logo" width="120" />
  <br>
  <h3>A powerful utility for converting and managing Telegram session files</h3>

  [![Python 3.7+](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Telethon](https://img.shields.io/badge/Telethon-Latest-brightgreen.svg)](https://github.com/LonamiWebs/Telethon)
  [![Pyrogram](https://img.shields.io/badge/Pyrogram-Latest-orange.svg)](https://github.com/pyrogram/pyrogram)
</div>

## ✨ Features

- 🔄 **Session Conversion**: Convert between Telethon and Pyrogram session formats
- 🔐 **String Sessions**: Generate portable string sessions from existing session files
- ✅ **Session Validation**: Verify the validity of session files
- 👤 **New Sessions**: Create new Telethon or Pyrogram sessions with login
- 🔢 **API Management**: Easy API credentials handling (file storage or direct input)
- 🖥️ **Multi-platform**: Works on Windows, macOS, and Linux
- 🎨 **User-friendly Interface**: Colorful, intuitive console interface

## 📋 Table of Contents

- [Installation](#-installation)
- [Dependencies](#-dependencies)
- [Usage](#-usage)
  - [Interactive Mode](#interactive-mode)
  - [Command-line Interface](#command-line-interface)
- [Examples](#-examples)
- [Troubleshooting](#-troubleshooting)
- [Security Notice](#-security-notice)
- [License](#-license)

## 🚀 Installation

### Option 1: Clone the repository

```bash
# Clone the repository
git clone https://github.com/yourusername/TGSessionsConverter.git

# Navigate to the project directory
cd TGSessionsConverter

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Install via pip

```bash
pip install TGSessionsConverter
```

## 📦 Dependencies

The project requires the following dependencies:

| Dependency | Description | Required |
|------------|-------------|----------|
| Telethon | Telegram client library for Python | Yes |
| Pyrogram | Modern Telegram client library | Yes |
| tgcrypto | Cryptography for Pyrogram | Yes |
| colorama | Colored terminal output | Optional |
| tqdm | Progress bars | Optional |
| nest_asyncio | Fix asyncio nested event loops | Optional |
| stream-sqlite | Stream SQLite databases | Optional |

## 💻 Usage

### Interactive Mode

The easiest way to use TGSessionsConverter is through its interactive console interface:

```bash
python tg_client_converter.py
```

This will launch the main menu where you can select various operations:

```
1. Create new Telethon session (login)
2. Create new Pyrogram session (login)
3. Convert Telethon session to Pyrogram
4. Convert Pyrogram session to Telethon
5. Convert session to String session
6. Check session validity
7. Delete session file
8. Create API credentials file
0. Exit
```

### Command-line Interface

TGSessionsConverter also offers a command-line interface for automation:

```bash
# Convert Telethon session to Pyrogram
python tg_client_converter.py convert --from telethon --to pyrogram --input telethon_session --output pyrogram_session --api-id YOUR_API_ID --api-hash YOUR_API_HASH

# Create a new Telethon session
python tg_client_converter.py login --type telethon --api-id YOUR_API_ID --api-hash YOUR_API_HASH --phone +1234567890

# Check session validity
python tg_client_converter.py check --session session_name --api-id YOUR_API_ID --api-hash YOUR_API_HASH

# Create API credentials file
python tg_client_converter.py config --api-id YOUR_API_ID --api-hash YOUR_API_HASH
```

## 📝 Examples

### Converting Pyrogram session to Telethon

```bash
python tg_client_converter.py convert --from pyrogram --to telethon --input my_pyrogram_session --output my_telethon_session
```

### Generating a String Session

```bash
python tg_client_converter.py convert --from telethon --to string --input my_telethon_session
```

### Creating an API credentials file

```bash
python tg_client_converter.py config
```

## ❓ Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Unknown DC ID" error | Make sure your session file is not corrupted and contains valid data |
| SQLite database is locked | Close any applications using the session file and try again |
| Import errors | Ensure all required dependencies are installed |
| Session validation fails | Your session may have expired or been revoked; create a new one |

### Logging

To enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Security Notice

**IMPORTANT**: 
- Session files and string sessions contain authentication data. Keep them secure.
- Never share your API ID, API Hash, or session files with others.
- Creating too many sessions in a short time may result in your account being limited.
- Use this tool responsibly and in accordance with Telegram's Terms of Service.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Made with ❤️ by VX</p>
  <p>
    <a href="https://github.com/yourusername">GitHub</a> •
    <a href="https://t.me/yourusername">Telegram</a>
  </p>
</div> 
