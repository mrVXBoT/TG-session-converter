#!/usr/bin/env python3
"""
Telegram Session Converter (TSC)

A sleek, standalone utility for managing and converting Telegram session files.

Features:
- Create new Telethon or Pyrogram sessions
- Convert between Telethon and Pyrogram session formats
- Generate string sessions
- Verify session validity
- Clean interface with colorful output

Author: YOUR_NAME_HERE
GitHub: https://github.com/YOUR_USERNAME_HERE/TGSessionsConverter
"""

import os
import sys
import time
import asyncio
import argparse
import platform
import sqlite3
import io
import base64
import struct
import re
import tempfile
from pathlib import Path
from typing import Union

# Try to import local modules
try:
    from tg_converter import main as tg_converter
    HAS_TG_CONVERTER = True
except ImportError:
    print("Warning: tg_converter module not found. Using built-in conversion methods.")
    HAS_TG_CONVERTER = False
    
try:
    from TgLiszt import telegram as tg_liszt
    HAS_TG_LISZT = True
except ImportError:
    print("Warning: TgLiszt module not found. Using built-in conversion methods.")
    HAS_TG_LISZT = False

# Try to import optional libraries with fallbacks
try:
    import nest_asyncio
    nest_asyncio.apply()  # Apply nest_asyncio to fix event loop issues
except ImportError:
    print("Warning: nest_asyncio not found. Some features may not work correctly.")
    print("You can install it with: pip install nest_asyncio")
    # Define a minimal fallback
    class DummyNestAsyncio:
        @staticmethod
        def apply(*args, **kwargs):
            pass
    nest_asyncio = DummyNestAsyncio()

try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama
    HAS_COLORAMA = True
except ImportError:
    print("Warning: colorama not found. Colored output disabled.")
    print("You can install it with: pip install colorama")
    HAS_COLORAMA = False
    
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    print("Warning: tqdm not found. Progress bars disabled.")
    print("You can install it with: pip install tqdm")
    HAS_TQDM = False

# Telethon imports with error handling
try:
    from telethon import TelegramClient as AsyncTelethonTelegramClient
    from telethon.sync import TelegramClient as SyncTelethonTelegramClient
    from telethon import functions, errors as telethon_errors
    from telethon.sync import TelegramClient, events
    from telethon.sessions import StringSession, MemorySession, SQLiteSession
    from telethon.crypto import AuthKey
    from telethon.version import __version__ as telethon_version
    from telethon.tl.types import Channel
    HAS_TELETHON = True
except ImportError:
    print("\n―― ⚠️ Telethon library not found. Some features will be disabled.")
    print("―― You can install it with: pip install telethon")
    HAS_TELETHON = False

# Pyrogram imports with error handling
try:
    from pyrogram import Client as PyrogramTelegramClient
    from pyrogram import filters, errors as pyrogram_errors
    from pyrogram.storage import MemoryStorage, FileStorage, Storage
    HAS_PYROGRAM = True
except ImportError:
    print("\n―― ⚠️ Pyrogram library not found. Some features will be disabled.")
    print("―― You can install it with: pip install pyrogram tgcrypto")
    HAS_PYROGRAM = False

# Stream-sqlite import with error handling
try:
    from stream_sqlite import stream_sqlite
    HAS_STREAM_SQLITE = True
except ImportError:
    print("\n―― ⚠️ stream-sqlite library not found. Some features will be disabled.")
    print("―― You can install it with: pip install stream-sqlite")
    HAS_STREAM_SQLITE = False

# Fallback dummy stream_sqlite function if the library is not available
if not HAS_STREAM_SQLITE:
    def stream_sqlite(file_obj, max_buffer_size=1048576):
        print("Error: stream_sqlite is not available. Please install it with: pip install stream-sqlite")
        return []

# Helper function to read API credentials from file
def read_api_credentials_from_file(filename="telegram_api.txt", print_func=print):
    """Read API credentials from a text file"""
    # Check multiple possible file locations
    possible_files = [
        filename,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        "api_credentials.txt",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_credentials.txt")
    ]
    
    for file_path in possible_files:
        try:
            if os.path.exists(file_path):
                print_func(f"Reading API credentials from {file_path}")
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    # Remove comments and empty lines
                    lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                    if len(lines) >= 2:
                        # Try to parse as API ID and API hash
                        try:
                            api_id = int(lines[0])
                            api_hash = lines[1]
                            return api_id, api_hash
                        except ValueError:
                            print_func(f"Invalid API ID in {file_path}")
                    else:
                        print_func(f"File {file_path} doesn't contain enough data")
        except Exception as e:
            print_func(f"Error reading {file_path}: {e}")
                
    return None, None

# Helper functions for Telegram interaction

def _show_warning() -> None:
    print(
        "\n―― ⚠️ WARNING: Frequently creating sessions and requesting OTPs may increase the risk of "
        "your account being temporarily or permanently banned."
        "\n―― Telegram monitors unusual activity, such as multiple login attempts in a short period of time."
        "\n―― Be cautious and avoid creating too many sessions too quickly."
        "\n―― ℹ️ Telegram ToS: https://core.telegram.org/api/terms"
        "\n―― ℹ️ Telethon FAQ: "
        "https://docs.telethon.dev/en/stable/quick-references/faq.html#my-account-was-deleted-limited-when-using-the-library\n")


def _handle_user_actions(client) -> None:
    if not HAS_TELETHON:
        print("Error: Telethon is required for this operation")
        return
        
    while True:
        print(
            f"\n―― [ 1 ] Get account's info"
            f"\n―― [ 2 ] See a list of user created Channels"
            f"\n―― [ 3 ] Update 2-Step Verification (2FA) password"
            f"\n―― [ 0 ] Exit"
        )

        user_input = input("\n―― Choose an option by typing its number: ")

        if user_input == "1":
            _show_user_info(client)
        elif user_input == "2":
            _show_user_channels(client)
        elif user_input == "3":
            _update_password(client)
        elif user_input == "0":
            if client.is_connected():
                client.disconnect()
            sys.exit(0)
        else:
            print("―― Invalid input! Please enter a valid option.\n")


def _show_user_info(client) -> None:
    if not HAS_TELETHON:
        print("Error: Telethon is required for this operation")
        return
        
    try:
        me = client.get_me()
        print(
            f"\n\t[ACCOUNT's INFO]\n"
            f"\tID: {me.id}\n"
            f"\tFirst Name: {me.first_name if me.first_name else '-'}\n"
            f"\tLast Name: {me.last_name if me.last_name else '-'}\n"
            f"\tUsername: {'@' + me.username if me.username else '-'}\n"
            f"\tPhone Number: +{me.phone}\n"
            f"\tPremium: {me.premium}\n"
            f"\tRestricted: {me.restricted}\n"
            f"\tFake: {me.fake}\n"
            f"\tScam: {me.scam}\n"
        )
    except telethon_errors.RPCError as e:
        print(f"―― ❌ An error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"―― ❌ An unexpected error occurred: {e}")
        sys.exit(1)


def _show_user_channels(client) -> None:
    if not HAS_TELETHON:
        print("Error: Telethon is required for this operation")
        return
        
    public_group = 0
    private_group = 0
    public_channel = 0
    private_channel = 0

    try:
        dialogs = client.get_dialogs()
        created_channels = [dialog for dialog in dialogs if isinstance(dialog.entity, Channel) and dialog.entity.creator]

        for channel in created_channels:
            e = channel.entity
            print(
                f"ID: {e.id}\n"
                f"Title: {e.title}\n"
                f"Username: {e.username if e.username else '-'}\n"
                f"Creation Date: {e.date.strftime('%Y-%m-%d')}\n"
                f"Link: {f'https://www.t.me/{e.username}' if e.username else '-'}\n"
            )

            if e.username:
                if e.megagroup:
                    public_group += 1
                else:
                    public_channel += 1
            else:
                if e.megagroup:
                    private_group += 1
                else:
                    private_channel += 1

        print(
            f"Public Groups: {public_group}\n"
            f"Private Groups: {private_group}\n"
            f"Public Channels: {public_channel}\n"
            f"Private Channels: {private_channel}\n"
        )
    except telethon_errors.RPCError as e:
        print(f"―― ❌ An error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"―― ❌ An unexpected error occurred: {e}")
        sys.exit(1)


def _update_password(client) -> None:
    if not HAS_TELETHON:
        print("Error: Telethon is required for this operation")
        return
        
    try:
        new_pwd = input("Enter your new 2FA password: ")
        client.edit_2fa(new_password=new_pwd)
        print(f"―― 🟢 2FA password has been updated successfully!")
    except telethon_errors.PasswordHashInvalidError:
        user_confirm = input(
            "―― ℹ️ 2-Step Verification (2FA) is already enabled on this account. "
            "To update it, you'll need to provide the current password.\n"
            "Would you like to proceed with changing your 2FA password? (y/n): "
        ).strip().lower()

        if user_confirm in {"y", "yes"}:
            curr_pwd = input("Enter your current 2FA password: ")
            new_pwd = input("Enter your new 2FA password: ")
            try:
                client.edit_2fa(current_password=curr_pwd, new_password=new_pwd)
                print(f"―― 🟢 2FA password has been updated successfully!")
            except telethon_errors.PasswordHashInvalidError:
                print("―― ❌ The current password you provided is incorrect.")
                sys.exit(1)
    except telethon_errors.RPCError as e:
        print(f"―― ❌ An error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"―― ❌ An unexpected error occurred: {e}")
        sys.exit(1)

# TelegramSession class for managing and converting session files
class TelegramSession:
    """Class for managing and converting Telegram session files"""

    DEFAULT_DEFICE_MODEL: str = "TGS {}".format(platform.uname().machine)
    DEFAULT_SYSTEM_VERSION: str = platform.uname().release
    DEFAULT_APP_VERSION: str = telethon_version if HAS_TELETHON else "Unknown"
    USE_NEST_ASYNCIO: bool = False
    
    def __init__(self, auth_key: bytes, dc_id, server_address, port, api_id: int, api_hash: str):
        self._auth_key = auth_key
        self._dc_id = dc_id
        self._server_address = server_address
        self._port = port
        self._api_id = api_id
        self._api_hash = api_hash
        self._loop = self.make_loop()

    @property
    def api_id(self):
        if self._api_id is None:
            raise ValueError("api_id is required for this method")
        return self._api_id

    @property
    def api_hash(self):
        if self._api_hash is None:
            raise ValueError("api_hash is required for this method")
        return self._api_hash

    @api_id.setter
    def api_id(self, value):
        self._api_id = value

    @api_hash.setter
    def api_hash(self, value):
        self._api_hash = value
    
    @staticmethod
    def make_loop():
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.get_event_loop()

    @staticmethod
    def from_sqlite_session_file_stream(
            sqlite_session: io.BytesIO, api_id: int, api_hash: str):
        """ Create  <TelegramSession> object from io.BytesIO object of read telethon session file(sqlite)
                return TelegramSession object
                    if sqlite_session is valid open as BytesIO telethon session
                        else -> None
        """
        if not isinstance(sqlite_session, io.BytesIO):
            raise TypeError(
                "sqlite_session must be io.BytesIO object of open and read sqlite3 session file")
        auth_key = None
        dc_id = None
        server_address = None
        port = None

        # Try to parse as Telethon session first
        telethon_session_found = False
        for table_name, table_info, rows in stream_sqlite(sqlite_session, max_buffer_size=1_048_576):
            if table_name == "sessions":
                telethon_session_found = True
                # This is likely a Telethon session
                for row in rows:
                    if hasattr(
                            row, "auth_key") and hasattr(
                                row, "dc_id") and hasattr(row, "server_address") and hasattr(row, "port"):
                        if row.auth_key is None:
                            continue
                        auth_key = row.auth_key
                        dc_id = row.dc_id
                        server_address = row.server_address
                        port = row.port
                        break
                break  # Exit the loop after checking sessions table

        # If Telethon session data not found, try Pyrogram format
        if not telethon_session_found or auth_key is None:
            # Reset file pointer
            sqlite_session.seek(0)
            
            try:
                pyrogram_data = TelegramSession._extract_pyrogram_session_data(sqlite_session)
                if pyrogram_data:
                    auth_key, dc_id, server_address, port = pyrogram_data
            except Exception as e:
                print(f"Error trying to extract Pyrogram session data: {e}")

        if (auth_key is None) or (dc_id is None) or (server_address is None) or (port is None):
            return None
            
        return TelegramSession(auth_key, dc_id, server_address, port, api_id, api_hash)

    @staticmethod
    def _extract_pyrogram_session_data(sqlite_session):
        """Extract session data from a Pyrogram session file"""
        try:
            # Reset the file pointer
            sqlite_session.seek(0)
            
            # Read the SQLite file as bytes
            db_bytes = sqlite_session.read()
            
            # Create a temporary file to work with the SQLite database
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(db_bytes)
                temp_path = temp_file.name
            
            # Connect to the SQLite database using the temp file
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Check if the sessions table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
            if not cursor.fetchone():
                conn.close()
                os.unlink(temp_path)
                return None
            
            # Get dc_id and auth_key from the Pyrogram session
            cursor.execute("SELECT * FROM sessions")
            session_data = cursor.fetchone()
            
            if session_data:
                try:
                    # Usually the format is:
                    # id, dc_id, test_mode, auth_key, date, user_id, is_bot
                    if len(session_data) >= 4:  # Make sure we have enough columns
                        dc_id = session_data[1]  # dc_id is usually the second column
                        auth_key = session_data[3]  # auth_key is usually the fourth column
                        
                        # Make sure we have valid data
                        if dc_id and auth_key:
                            # Get server address and port based on dc_id
                            dc_maps = {
                                1: {'serverAddress': '149.154.175.53', 'port': 443},
                                2: {'serverAddress': '149.154.167.51', 'port': 443},
                                3: {'serverAddress': '149.154.175.100', 'port': 443},
                                4: {'serverAddress': '149.154.167.91', 'port': 443},
                                5: {'serverAddress': '91.108.56.130', 'port': 443}
                            }
                            
                            if dc_id in dc_maps:
                                server_address = dc_maps[dc_id]['serverAddress']
                                port = dc_maps[dc_id]['port']
                                
                                # Close and clean up
                                conn.close()
                                os.unlink(temp_path)
                                
                                return auth_key, dc_id, server_address, port
                except Exception as e:
                    print(f"Error processing session data: {e}")
            
            # Clean up if we get here
            conn.close()
            os.unlink(temp_path)
            return None
        except sqlite3.Error as e:
            print(f"SQLite error extracting Pyrogram session data: {e}")
            return None
        except Exception as e:
            print(f"General error extracting Pyrogram session data: {e}")
            return None

    @staticmethod
    def from_sqlite_session_file(id_or_path: Union[str, io.BytesIO], api_id: int, api_hash: str):
        sqlite_session = id_or_path
        if isinstance(id_or_path, str):
            # Check if we need to add .session extension
            session_path = id_or_path
            if not session_path.endswith('.session'):
                session_path = f"{session_path}.session"
                
            try:
                with open(session_path, "rb") as file:
                    sqlite_session = io.BytesIO(file.read())
            except FileNotFoundError as exp:
                # Try original path as a fallback
                try:
                    with open(id_or_path, "rb") as file:
                        sqlite_session = io.BytesIO(file.read())
                except Exception:
                    raise exp
        else:
            if not isinstance(id_or_path, io.BytesIO):
                raise TypeError("id_or_path must be str name or io.BytesIO object")

        return TelegramSession.from_sqlite_session_file_stream(sqlite_session, api_id, api_hash)

    @staticmethod
    def from_telethon_or_pyrogram_client(
            client: Union[
                AsyncTelethonTelegramClient, SyncTelethonTelegramClient, PyrogramTelegramClient]):
        if HAS_TELETHON and isinstance(client, (AsyncTelethonTelegramClient, SyncTelethonTelegramClient)):
            # is Telethon
            api_hash = str(client.api_hash)
            if api_hash == str(client.api_id):
                api_hash = None
            return TelegramSession(
                client.session.auth_key.key,
                client.session.dc_id,
                client.session.server_address,
                client.session.port,
                client.api_id, api_hash
            )
        elif HAS_PYROGRAM and isinstance(client, PyrogramTelegramClient):
            # Pyrogram handling would go here
            pass
        else:
            raise TypeError("client must be <telethon.TelegramClient> or <pyrogram.Client> instance")

    def _make_telethon_memory_session_storage(self):
        if not HAS_TELETHON:
            print("Error: Telethon is required for this operation")
            return None
            
        session = MemorySession()
        session.set_dc(self._dc_id, self._server_address, self._port)
        session.auth_key = AuthKey(data=self._auth_key)
        return session

    def _make_telethon_sqlite_session_storoge(
            self, id_or_path: str = "telethon", update_table=False, save=False):
        if not HAS_TELETHON:
            print("Error: Telethon is required for this operation")
            return None
            
        session_storage = SQLiteSession(id_or_path)
        session_storage.set_dc(self._dc_id, self._server_address, self._port)
        session_storage.auth_key = AuthKey(data=self._auth_key)
        if update_table:
            session_storage._update_session_table()
        if save:
            session_storage.save()
        return session_storage

    def make_telethon(
            self, session=None, sync=False, **make_args) -> Union[
                AsyncTelethonTelegramClient, SyncTelethonTelegramClient, None]:
        """
            Create <telethon.TelegramClient> client object with current session data
        """
        if not HAS_TELETHON:
            print("Error: Telethon is required for this operation")
            return None
            
        if session is None:
            session = self._make_telethon_memory_session_storage()
        THClientMake = AsyncTelethonTelegramClient
        if sync:
            THClientMake = SyncTelethonTelegramClient
        return THClientMake(session, self.api_id, self.api_hash, **make_args)

    async def make_pyrogram(self, session_id: str = "pyrogram", **make_args):
        """
            Create <pyrogram.Client> client object with current session data
                using in_memory session storoge
        """
        if not HAS_TELETHON or not HAS_PYROGRAM:
            print("Error: Both Telethon and Pyrogram are required for this operation")
            return None
            
        th_client = self.make_telethon()
        if not th_client:
            return None
        async with th_client:
            user_data = await th_client.get_me()

        pyrogram_string_session = base64.urlsafe_b64encode(
            struct.pack(
                Storage.SESSION_STRING_FORMAT,
                self._dc_id,
                self.api_id,
                False,
                self._auth_key,
                int(user_data.id or 999999999),
                0
            )
        ).decode().rstrip("=")
        client = PyrogramTelegramClient(
            session_id, session_string=pyrogram_string_session,
            api_id=self.api_id, api_hash=self.api_hash, **make_args)
        return client

    def make_sqlite_session_file(
            self, client_id: str = "telegram",
            workdir: str = None, pyrogram: bool = False,
            api_id: int = None, api_hash: str = None, **make_args) -> bool:
        """ Make telethon sqlite3 session file
                {id.session} will be created if id_or_path is not the full path to the file
        """
        session_workdir = Path.cwd()
        if workdir is not None:
            session_workdir = Path(workdir)
        session_path = "{}/{}.session".format(session_workdir, client_id)
        
        if pyrogram:
            if not HAS_PYROGRAM:
                print("Error: Pyrogram is required for this operation")
                return False
                
            session_workdir = Path.cwd()
            if workdir is not None:
                session_workdir = Path(workdir)

            # Create pyrogram session
            client = PyrogramTelegramClient(
                client_id,
                api_id=api_id or self.api_id,api_hash=api_hash or self.api_hash,
                **make_args)
            client.storage = FileStorage(client_id, session_workdir)
            client.storage.conn = sqlite3.Connection(session_path)
            client.storage.create()

            async def async_wrapper(client):
                user_id = 999999999
                th_client = self.make_telethon(sync=False, **make_args)
                if th_client:
                    async with th_client:
                        user_data = await th_client.get_me()
                        user_id = user_data.id

                await client.storage.dc_id(self._dc_id)
                await client.storage.api_id(self.api_id)
                await client.storage.test_mode(False)
                await client.storage.auth_key(self._auth_key)
                await client.storage.user_id(user_id)
                await client.storage.date(0)
                await client.storage.is_bot(False)
                await client.storage.save()
            if self.USE_NEST_ASYNCIO:
                nest_asyncio.apply(self._loop)
            self._loop.run_until_complete(async_wrapper(client))
            
        else:
            if not HAS_TELETHON:
                print("Error: Telethon is required for this operation")
                return False
                
            self._make_telethon_sqlite_session_storoge(session_path, update_table=True, save=True)
        return True

# SessionManager class for session creation
class SessionManager:
    """
    Create Telegram sessions using Telethon or Pyrogram.
    """

    @staticmethod
    def telethon(api_id: int = None, api_hash: str = None, phone: str = None) -> None:
        """
        Create Telethon Sessions.

        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param phone: Phone number in international format. If you want to generate a string session,
               enter your telethon session file name instead.
        """
        if not HAS_TELETHON:
            print("\n―― ❌ Telethon is required for this operation. Please install it with: pip install telethon")
            return

        _show_warning()

        user_api_id = api_id or int(input("Enter your API ID: "))
        user_api_hash = api_hash or input("Enter your API HASH: ")
        user_phone = phone or input("Enter your phone number (e.g. +1234567890): ")

        try:
            client = TelegramClient(f'{user_phone}.session', user_api_id, user_api_hash)
            client.connect()
            if not client.is_user_authorized():
                client.send_code_request(user_phone)
                try:
                    client.sign_in(user_phone, input("Enter the code sent to your phone: "))
                except telethon_errors.SessionPasswordNeededError:
                    client.sign_in(password=input("Enter 2-Step Verification (2FA) password: "))
        except sqlite3.OperationalError:
            print(
                "\n―― ❌ The provided session file could not be opened. "
                "This issue may occur if the session file was created using a different library or is corrupted. "
                "Please ensure that the session file is compatible with Telethon."
            )
            sys.exit(1)
        except telethon_errors.RPCError as e:
            print(f"\n―― ❌ An RPC error occurred: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n―― ❌ An unexpected error occurred: {e}")
            sys.exit(1)

        print(
            f"\n―― 🟢 TELETHON SESSION ↓"
            f"\n―― ✨ SESSION FILE saved as `{user_phone}{'.session' if not user_phone.endswith('.session') else ''}`"
            f"\n―― ✨ STRING SESSION: {StringSession.save(client.session)}"
        )

        _handle_user_actions(client)

    @staticmethod
    def pyrogram(api_id: int = None, api_hash: str = None, phone: str = None) -> None:
        """
        Create Pyrogram Sessions.

        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param phone: Phone number in international format. If you want to generate a string session,
               enter your pyrogram session file name instead.
        """
        if not HAS_PYROGRAM:
            print("\n―― ❌ Pyrogram is required for this operation. Please install it with: pip install pyrogram tgcrypto")
            return

        _show_warning()

        user_api_id = api_id or int(input("Enter your API ID: "))
        user_api_hash = api_hash or input("Enter your API HASH: ")
        user_phone = phone or input("Enter your phone number (e.g. +1234567890): ")

        try:
            client = PyrogramTelegramClient(user_phone, user_api_id, user_api_hash, phone_number=user_phone)
            client.start()
        except sqlite3.OperationalError:
            print(
                "\n―― ❌ The provided session file could not be opened. "
                "This issue may occur if the session file was created using a different library or is corrupted. "
                "Please ensure that the session file is compatible with Pyrogram."
            )
            sys.exit(1)
        except pyrogram_errors.RPCError as e:
            print(f"\n―― ❌ An RPC error occurred: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n―― ❌ An unexpected error occurred: {e}")
            sys.exit(1)

        print(
            f"\n―― 🟢 PYROGRAM SESSION ↓"
            f"\n―― ✨ SESSION FILE saved as `{user_phone}{'.session' if not user_phone.endswith('.session') else ''}`"
            f"\n―― ✨ STRING SESSION: {client.export_session_string()}")

        client.stop()
        sys.exit(0)

# Telegram class for interaction
class Telegram:
    """
    Interact with Telegram.
    """

    @staticmethod
    def login(api_id: int = None, api_hash: str = None, session_name: str = None) -> None:
        """
        Login to Telegram using Telethon session file.
        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param session_name: Your Telethon session file name
        """
        if not HAS_TELETHON:
            print("\n―― ❌ Telethon is required for this operation. Please install it with: pip install telethon")
            return
            
        print(
            "\n―― ℹ️ This method only supports Telethon session files. If you're using Pyrogram, "
            "please switch to Telethon for this function to work properly."
        )

        user_api_id = api_id or int(input("Enter your API ID: "))
        user_api_hash = api_hash or input("Enter your API HASH: ")
        user_session_name = session_name or input("Enter your Telethon session file name: ")

        try:
            client = TelegramClient(user_session_name, user_api_id, user_api_hash)
            client.connect()
            if client.is_user_authorized():
                print("\n―― 🟢 User Authorized!")

                @client.on(events.NewMessage(from_users=777000))
                async def get_otp_msg(event):
                    otp = re.search(r'\b(\d{5})\b', event.raw_text)
                    if otp:
                        print("\n―― OTP received ✅\n―― Your login code:", otp.group(0))
                        client.disconnect()
                        sys.exit(0)

                print("\n―― Please request an OTP code in your Telegram app."
                      "\n―― 📲 𝙻𝚒𝚜𝚝𝚎𝚗𝚒𝚗𝚐 𝚏𝚘𝚛 𝚒𝚗𝚌𝚘𝚖𝚒𝚗𝚐 𝙾𝚃𝙿 . . .")
             
            else:
                print("\n―― 🔴 Authorization Failed!"
                      "\n―― The session has been revoked or is invalid.")
                sys.exit(1)
        except sqlite3.OperationalError:
            print(
                "\n―― ❌ The provided session file could not be opened. "
                "This issue may occur if the session file was created using a different library or is corrupted. "
                "Please ensure that the session file is compatible with Telethon."
            )
            sys.exit(1)
        except telethon_errors.RPCError as e:
            print(f"\n―― ❌ An RPC error occurred: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n―― ❌ An unexpected error occurred: {e}")
            sys.exit(1)

# Main converter class
class TelegramSessionConverter:
    """Main class for the Telegram Session Converter utility"""
    
    def __init__(self):
        """Initialize the Telegram session converter"""
        self.api_id = None
        self.api_hash = None
        self.version = "1.0.0 VX"
    
    def colored_print(self, text, color=None, bright=False, bold=False):
        """Print colored text if colorama is available"""
        if HAS_COLORAMA:
            color_code = getattr(Fore, color.upper()) if color else ""
            style_code = Style.BRIGHT if bright else ""
            bold_code = "\033[1m" if bold else ""
            print(f"{bold_code}{style_code}{color_code}{text}{Style.RESET_ALL}")
        else:
            print(text)
    
    def print_header(self, title):
        """Display a formatted header"""
        terminal_width = 80
        try:
            # Get terminal width on supported platforms
            terminal_width = os.get_terminal_size().columns
        except:
            pass
            
        # Add VX branding if not already in the title
        if "VX" not in title:
            title = f"{title} | VX"
            
        if HAS_COLORAMA:
            border_color = Fore.BLUE
            title_color = Fore.CYAN + Style.BRIGHT
            reset = Style.RESET_ALL
            
            # Create a fancy header with double borders
            print(f"\n{border_color}╔{'═' * (terminal_width - 2)}╗{reset}")
            print(f"{border_color}║{title_color}{title.center(terminal_width - 2)}{border_color}║{reset}")
            print(f"{border_color}╚{'═' * (terminal_width - 2)}╝{reset}\n")
        else:
            print("\n" + "=" * terminal_width)
            print(title.center(terminal_width))
            print("=" * terminal_width + "\n")
    
    def print_logo(self):
        """Display an ASCII art logo"""
        if HAS_COLORAMA:
            primary_color = Fore.CYAN
            accent_color = Fore.MAGENTA
            version_color = Fore.GREEN
            reset = Style.RESET_ALL
        else:
            primary_color = ""
            accent_color = ""
            version_color = ""
            reset = ""
            
        logo = f"""
{primary_color}  _______   _______   _______              {accent_color} __     __  __   __      {reset}
{primary_color} |__   __| |  ____| |__   __|             {accent_color} \ \   / / \ \ / /      {reset}
{primary_color}    | |    | |  __     | |     ___    ___ {accent_color}  \ \ / /   \ V /       {reset}
{primary_color}    | |    | | |_ |    | |    / __|  / __|{accent_color}   \   /     > <        {reset}
{primary_color}    | |    | |__| |    | |    \__ \ | (__ {accent_color}    | |     / . \       {reset}
{primary_color}    |_|    |______|    |_|    |___/  \___|{accent_color}    |_|    /_/ \_\      {reset}
                                                                                
{primary_color}  _____                                _              {reset}
{primary_color} / ____|                              | |             
{primary_color}| (___    ___  ___  ___  ___   ___   | |_   ___  ___ 
{primary_color} \___ \  / _ \/ __|/ __|/ __| / _ \  | __| / _ \/ __|
{primary_color} ____) ||  __/\__ \\__ \\__ \| (_) | | |_ |  __/\__ \\
{primary_color}|_____/  \___||___/|___/|___/ \___/   \__| \___||___/{reset}
                                                        
{primary_color}  _____                               _              
{primary_color} / ____|                             | |             
{primary_color}| |      ___   _ __  __   __  ___  _ | |_  ___  _ __ 
{primary_color}| |     / _ \ | '_ \ \ \ / / / _ \| || __|/ _ \| '__|
{primary_color}| |____| (_) || | | | \ V / |  __/| || |_|  __/| |   
{primary_color} \_____|\___/ |_| |_|  \_/   \___||_| \__|\___||_|   {reset}
"""
        print(logo)
        print(f"{version_color}Version {self.version} | VX Edition{reset}".center(80))
        print()
        
        # Add a decorative separator
        if HAS_COLORAMA:
            separator = f"{accent_color}{'═' * 100}{reset}"
        else:
            separator = "═" * 100
        print(separator)
    
    def get_api_credentials(self):
        """Get API credentials from user, environment variables, or file"""
        # First check for credentials file
        def colored_print_wrapper(text, color=None):
            self.colored_print(text, color)
            
        api_id, api_hash = read_api_credentials_from_file(print_func=colored_print_wrapper)
        if api_id and api_hash:
            self.colored_print("Using API credentials from credentials file", "green")
            self.api_id = api_id
            self.api_hash = api_hash
            return True
            
        # Check environment variables
        api_id = os.environ.get('TG_API_ID')
        api_hash = os.environ.get('TG_API_HASH')
        
        if api_id and api_hash:
            self.colored_print("Using API credentials from environment variables", "green")
            try:
                self.api_id = int(api_id)
                self.api_hash = api_hash
                return True
            except ValueError:
                self.colored_print("Invalid API ID in environment variables", "red")
        
        # If not in file or environment, ask the user
        if not self.api_id or not self.api_hash:
            self.colored_print("To use this program, you need Telegram API credentials", "yellow")
            self.colored_print("You can get them from https://my.telegram.org/apps", "yellow")
            print()
            
            try:
                api_id = input("Enter your API ID: ")
                self.api_id = int(api_id)
                self.api_hash = input("Enter your API Hash: ")
                return True
            except ValueError:
                self.colored_print("API ID must be a number", "red")
                return False
        
        return True
        
    def show_progress(self, description, total=10):
        """Show a progress bar for operations that take time"""
        if HAS_TQDM:
            for i in tqdm(range(total), desc=description):
                time.sleep(0.1)
        else:
            print(description + "... ", end="", flush=True)
            for _ in range(5):
                time.sleep(0.2)
                print(".", end="", flush=True)
            print(" Done!")
    
    def show_main_menu(self):
        """Display the main menu options"""
        self.print_logo()
        self.print_header("MAIN MENU | VX EDITION")
        
        # Define menu categories
        session_options = [
            ("1", "Create new Telethon session (login)"),
            ("2", "Create new Pyrogram session (login)")
        ]
        
        conversion_options = [
            ("3", "Convert Telethon session to Pyrogram"),
            ("4", "Convert Pyrogram session to Telethon"),
            ("5", "Convert session to String session")
        ]
        
        utility_options = [
            ("6", "Check session validity"),
            ("7", "Delete session file"),
            ("8", "Create API credentials file")
        ]
        
        exit_option = [("0", "Exit")]
        
        # Calculate the maximum width needed for the table
        max_width = max(
            max(len(text) for _, text in session_options),
            max(len(text) for _, text in conversion_options),
            max(len(text) for _, text in utility_options)
        ) + 10  # Add some padding
        
        # Print the menu in a tabular format
        if HAS_COLORAMA:
            header_color = Fore.YELLOW + Style.BRIGHT
            category_color = Fore.MAGENTA + Style.BRIGHT
            key_color = Fore.GREEN + Style.BRIGHT
            text_color = Fore.WHITE
            border_color = Fore.BLUE
            reset = Style.RESET_ALL
        else:
            header_color = ""
            category_color = ""
            key_color = ""
            text_color = ""
            border_color = ""
            reset = ""
        
        # Print table borders and headers
        print(f"{border_color}┌{'─' * (max_width + 8)}┐{reset}")
        print(f"{border_color}│{category_color} 🔐 SESSION MANAGEMENT {' ' * (max_width - 15)}│{reset}")
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        
        # Print session options
        for key, text in session_options:
            print(f"{border_color}│ {key_color}[{key}]{reset} {text_color}{text}{' ' * (max_width - len(text))}{border_color}│{reset}")
        
        # Print conversion category
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        print(f"{border_color}│{category_color} 🔄 SESSION CONVERSION {' ' * (max_width - 15)}│{reset}")
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        
        # Print conversion options
        for key, text in conversion_options:
            print(f"{border_color}│ {key_color}[{key}]{reset} {text_color}{text}{' ' * (max_width - len(text))}{border_color}│{reset}")
        
        # Print utility category
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        print(f"{border_color}│{category_color} 🛠️  UTILITIES {' ' * (max_width - 8)}│{reset}")
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        
        # Print utility options
        for key, text in utility_options:
            print(f"{border_color}│ {key_color}[{key}]{reset} {text_color}{text}{' ' * (max_width - len(text))}{border_color}│{reset}")
        
        # Print exit option
        print(f"{border_color}├{'─' * (max_width + 8)}┤{reset}")
        for key, text in exit_option:
            print(f"{border_color}│ {key_color}[{key}]{reset} {text_color}{text}{' ' * (max_width - len(text))}{border_color}│{reset}")
        
        print(f"{border_color}└{'─' * (max_width + 8)}┘{reset}")
        
        choice = input(f"\n{key_color}Enter your choice (0-8):{reset} ")
        return choice
    
    def delete_session(self):
        """Delete a session file"""
        self.print_header("Delete Session File")
        
        session_path = input("Enter the session file path to delete: ")
        
        # Ensure the session file exists
        if not session_path.endswith('.session'):
            session_file = f"{session_path}.session"
        else:
            session_file = session_path
        
        if not os.path.exists(session_file):
            self.colored_print(f"Error: Session file not found: {session_file}", "red")
            input("\nPress Enter to return to main menu...")
            return
            
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete {session_file}? (yes/no): ")
        if confirm.lower() not in ('yes', 'y'):
            self.colored_print("Deletion cancelled", "yellow")
            input("\nPress Enter to return to main menu...")
            return
            
        # Delete the file
        try:
            os.remove(session_file)
            self.colored_print(f"Session file {session_file} deleted successfully", "green")
        except Exception as e:
            self.colored_print(f"Error deleting session file: {e}", "red")
            
        input("\nPress Enter to return to main menu...")
    
    def login_and_create_session(self, session_type):
        """Login to Telegram and create a new session"""
        self.print_header(f"Creating new {session_type.capitalize()} session")
        
        if not self.get_api_credentials():
            input("\nPress Enter to continue...")
            return
        
        phone = input("\nEnter your phone number (e.g. +1234567890): ")
        
        try:
            if session_type == "telethon":
                if not HAS_TELETHON:
                    self.colored_print("\nError: Telethon is required for this operation. Please install it with: pip install telethon", "red")
                    input("\nPress Enter to continue...")
                    return
                    
                self.colored_print("\nStarting Telethon login process...", "blue")
                self.show_progress("Connecting to Telegram")
                SessionManager.telethon(self.api_id, self.api_hash, phone)
            elif session_type == "pyrogram":
                if not HAS_PYROGRAM:
                    self.colored_print("\nError: Pyrogram is required for this operation. Please install it with: pip install pyrogram tgcrypto", "red")
                    input("\nPress Enter to continue...")
                    return
                    
                self.colored_print("\nStarting Pyrogram login process...", "blue")
                self.show_progress("Connecting to Telegram")
                SessionManager.pyrogram(self.api_id, self.api_hash, phone)
            
            self.colored_print("\nSession created successfully!", "green")
        except Exception as e:
            self.colored_print(f"\nError creating session: {e}", "red")
        
        input("\nPress Enter to return to main menu...")
    
    def check_session(self):
        """Check if a session is valid and display its information"""
        self.print_header("Check Session Validity | VX")
        
        if not self.get_api_credentials():
            input("\nPress Enter to continue...")
            return
        
        session_name = input("\nEnter the session name to check: ")
        
        # Ensure the session file exists
        if not session_name.endswith('.session'):
            session_file = f"{session_name}.session"
        else:
            session_file = session_name
        
        if not os.path.exists(session_file):
            self.colored_print(f"\nError: Session file not found: {session_file}", "red")
            input("\nPress Enter to return to main menu...")
            return
        
        # Try to login with the existing session
        try:
            self.colored_print("\nChecking session validity...", "blue")
            self.show_progress("Verifying session")
            
            # Get basic file info first
            file_size = os.path.getsize(session_file)
            mod_time = os.path.getmtime(session_file)
            mod_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
            
            # Determine session type (basic check)
            session_type = "Unknown"
            try:
                with sqlite3.connect(session_file) as conn:
                    cursor = conn.cursor()
                    # Check for Telethon-specific tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                    if cursor.fetchone():
                        # Further check for format
                        cursor.execute("PRAGMA table_info(sessions)")
                        columns = [col[1] for col in cursor.fetchall()]
                        if 'server_address' in columns:
                            session_type = "Telethon"
                        elif 'dc_id' in columns and 'api_id' in columns:
                            session_type = "Pyrogram"
            except:
                pass
            
            # Display session file information in a table
            if HAS_COLORAMA:
                border_color = Fore.BLUE
                header_color = Fore.YELLOW + Style.BRIGHT
                value_color = Fore.GREEN
                reset = Style.RESET_ALL
            else:
                border_color = ""
                header_color = ""
                value_color = ""
                reset = ""
                
            # Create a table with session file information
            print(f"\n{border_color}┌{'─' * 50}┐{reset}")
            print(f"{border_color}│{header_color} SESSION FILE INFORMATION {' ' * 27}│{reset}")
            print(f"{border_color}├{'─' * 50}┤{reset}")
            print(f"{border_color}│{reset} File path: {value_color}{session_file}{' ' * (40 - len(session_file))}{border_color}│{reset}")
            print(f"{border_color}│{reset} File size: {value_color}{file_size} bytes{' ' * (38 - len(str(file_size)))}{border_color}│{reset}")
            print(f"{border_color}│{reset} Modified: {value_color}{mod_date}{' ' * (40 - len(mod_date))}{border_color}│{reset}")
            print(f"{border_color}│{reset} Type: {value_color}{session_type}{' ' * (44 - len(session_type))}{border_color}│{reset}")
            print(f"{border_color}└{'─' * 50}┘{reset}")
            
            # Try to initialize Telegram with the session
            print(f"\n{border_color}Attempting to connect using the session...{reset}")
            Telegram.login(self.api_id, self.api_hash, session_name.replace('.session', ''))
            
            self.colored_print("\n✅ Session is valid! Authentication successful.", "green", bold=True)
        except Exception as e:
            self.colored_print(f"\n❌ Session is invalid: {e}", "red", bold=True)
        
        input("\nPress Enter to return to main menu...")
    
    async def convert_session_async(self, from_format, to_format, input_path, output_path=None, delete_original=False):
        """Core conversion function that handles the async work"""
        
        # First try using the specialized modules if available
        if HAS_TG_CONVERTER:
            self.colored_print("\nUsing tg_converter module for conversion...", "blue")
            try:
                self.show_progress("Converting with tg_converter")
                
                if from_format == "pyrogram" and to_format == "telethon":
                    # Call the appropriate function from tg_converter
                    if not output_path:
                        output_path = "telethon.session"
                    if not output_path.endswith('.session'):
                        output_path = f"{output_path}.session"
                        
                    # Import and use tg_converter functionality
                    result = tg_converter.convert_pyrogram_to_telethon(
                        input_path, 
                        output_path, 
                        self.api_id, 
                        self.api_hash
                    )
                    
                    if result:
                        self.colored_print(f"\nSuccessfully converted to {output_path}", "green")
                        
                        # Delete original if requested
                        if delete_original and from_format != to_format:
                            try:
                                os.remove(input_path)
                                self.colored_print(f"Original session file {input_path} deleted", "yellow")
                            except Exception as e:
                                self.colored_print(f"Error deleting original session: {e}", "red")
                        
                        return True
                elif to_format == "string":
                    # Try to convert to string session using tg_converter
                    try:
                        # For Pyrogram to string session
                        if from_format == "pyrogram":
                            # Use direct method to read Pyrogram session and extract data
                            import sqlite3
                            from pyrogram.storage import Storage
                            
                            # Ensure input path has .session extension
                            if not input_path.endswith('.session'):
                                input_path = f"{input_path}.session"
                                
                            if not os.path.exists(input_path):
                                self.colored_print(f"Error: Session file not found: {input_path}", "red")
                                return False
                                
                            # Read Pyrogram session directly
                            try:
                                conn = sqlite3.connect(input_path)
                                cursor = conn.cursor()
                                
                                # Get column names
                                cursor.execute("PRAGMA table_info(sessions)")
                                columns = [col[1] for col in cursor.fetchall()]
                                
                                # Get session data
                                cursor.execute("SELECT * FROM sessions")
                                session_data = cursor.fetchone()
                                
                                if not session_data:
                                    self.colored_print("Error: No session data found in Pyrogram session", "red")
                                    conn.close()
                                    return False
                                    
                                # Map columns to values
                                session_dict = {columns[i]: session_data[i] for i in range(len(columns))}
                                
                                # Extract the necessary data
                                dc_id = session_dict.get('dc_id')
                                api_id = self.api_id
                                test_mode = session_dict.get('test_mode', False)
                                auth_key = session_dict.get('auth_key')
                                user_id = session_dict.get('user_id', 0)
                                is_bot = session_dict.get('is_bot', False)
                                
                                conn.close()
                                
                                # Create the string session
                                if None not in (dc_id, auth_key):
                                    string_session = base64.urlsafe_b64encode(
                                        struct.pack(
                                            Storage.SESSION_STRING_FORMAT,
                                            dc_id,
                                            api_id,
                                            test_mode,
                                            auth_key,
                                            user_id,
                                            is_bot
                                        )
                                    ).decode().rstrip("=")
                                    
                                    self.colored_print("\nPyrogram String Session (keep this private):", "green", bold=True)
                                    
                                    # Display string session in a box
                                    if HAS_COLORAMA:
                                        border = f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}"
                                        print(border)
                                        print(f"{Fore.GREEN}{string_session}{Style.RESET_ALL}")
                                        print(border)
                                    else:
                                        border = '=' * 80
                                        print(border)
                                        print(string_session)
                                        print(border)
                                        
                                    # Save to file option
                                    save_option = input("\nDo you want to save this string session to a file? (yes/no): ")
                                    if save_option.lower() in ('yes', 'y'):
                                        file_name = input("Enter filename (or press Enter for 'string_session.txt'): ") or "string_session.txt"
                                        try:
                                            with open(file_name, 'w') as f:
                                                f.write(string_session)
                                            self.colored_print(f"String session saved to {file_name}", "green")
                                        except Exception as e:
                                            self.colored_print(f"Error saving to file: {e}", "red")
                                    
                                    return True
                                else:
                                    self.colored_print("Error: Missing required data in Pyrogram session", "red")
                                    return False
                            except Exception as e:
                                self.colored_print(f"Error reading Pyrogram session: {e}", "red")
                                return False
                    except Exception as e:
                        self.colored_print(f"Error in tg_converter string session generation: {e}", "yellow")
                        # Continue to built-in methods
            except Exception as e:
                self.colored_print(f"\nError using tg_converter: {e}", "yellow")
                self.colored_print("Falling back to built-in methods...", "yellow")
        
        elif HAS_TG_LISZT:
            self.colored_print("\nUsing TgLiszt module for conversion...", "blue")
            try:
                self.show_progress("Converting with TgLiszt")
                
                if from_format == "pyrogram" and to_format == "telethon":
                    # Call the appropriate function from TgLiszt
                    if not output_path:
                        output_path = "telethon.session"
                    if not output_path.endswith('.session'):
                        output_path = f"{output_path}.session"
                        
                    # Import and use TgLiszt functionality
                    result = tg_liszt.convert_session(
                        input_path, 
                        output_path, 
                        from_format="pyrogram",
                        to_format="telethon",
                        api_id=self.api_id,
                        api_hash=self.api_hash
                    )
                    
                    if result:
                        self.colored_print(f"\nSuccessfully converted to {output_path}", "green")
                        
                        # Delete original if requested
                        if delete_original and from_format != to_format:
                            try:
                                os.remove(input_path)
                                self.colored_print(f"Original session file {input_path} deleted", "yellow")
                            except Exception as e:
                                self.colored_print(f"Error deleting original session: {e}", "red")
                        
                        return True
            except Exception as e:
                self.colored_print(f"\nError using TgLiszt: {e}", "yellow")
                self.colored_print("Falling back to built-in methods...", "yellow")
        
        # If we got here, use the built-in methods
        self.colored_print("\nUsing built-in conversion methods...", "blue")
        
        # Create TelegramSession object from the input format
        session = None
        
        # Check required libraries
        if not HAS_STREAM_SQLITE:
            self.colored_print("\nError: stream-sqlite library is required for conversion operations.", "red")
            self.colored_print("Please install it with: pip install stream-sqlite", "yellow")
            return False
            
        if from_format == "telethon" and not HAS_TELETHON:
            self.colored_print("\nError: Telethon is required for this operation.", "red")
            self.colored_print("Please install it with: pip install telethon", "yellow")
            return False
            
        if (from_format == "pyrogram" or to_format == "pyrogram" or to_format == "string") and not HAS_PYROGRAM:
            self.colored_print("\nError: Pyrogram is required for this operation.", "red")
            self.colored_print("Please install it with: pip install pyrogram tgcrypto", "yellow")
            return False
        
        # Special case for string session conversion from Pyrogram
        if from_format == "pyrogram" and to_format == "string":
            try:
                import sqlite3
                from pyrogram.storage import Storage
                
                # Ensure input path has .session extension
                if not input_path.endswith('.session'):
                    input_path = f"{input_path}.session"
                    
                if not os.path.exists(input_path):
                    self.colored_print(f"\nError: Session file not found: {input_path}", "red")
                    return False
                    
                self.colored_print(f"\nConverting from pyrogram session file: {input_path}", "blue")
                self.show_progress("Reading session file")
                
                # Read Pyrogram session directly
                try:
                    conn = sqlite3.connect(input_path)
                    cursor = conn.cursor()
                    
                    # Get column names
                    cursor.execute("PRAGMA table_info(sessions)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Get session data
                    cursor.execute("SELECT * FROM sessions")
                    session_data = cursor.fetchone()
                    
                    if not session_data:
                        self.colored_print("\nError: No session data found in Pyrogram session", "red")
                        conn.close()
                        return False
                        
                    # Map columns to values
                    session_dict = {columns[i]: session_data[i] for i in range(len(columns))}
                    
                    # Extract the necessary data
                    dc_id = session_dict.get('dc_id')
                    api_id = self.api_id
                    test_mode = session_dict.get('test_mode', False)
                    auth_key = session_dict.get('auth_key')
                    user_id = session_dict.get('user_id', 0)
                    is_bot = session_dict.get('is_bot', False)
                    
                    conn.close()
                    
                    # Generate string session
                    self.show_progress("Generating string session")
                    
                    if None not in (dc_id, auth_key):
                        string_session = base64.urlsafe_b64encode(
                            struct.pack(
                                Storage.SESSION_STRING_FORMAT,
                                dc_id,
                                api_id,
                                test_mode,
                                auth_key,
                                user_id,
                                is_bot
                            )
                        ).decode().rstrip("=")
                        
                        self.colored_print("\nPyrogram String Session (keep this private):", "green", bold=True)
                        
                        # Display string session in a box
                        if HAS_COLORAMA:
                            border = f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}"
                            print(border)
                            print(f"{Fore.GREEN}{string_session}{Style.RESET_ALL}")
                            print(border)
                        else:
                            border = '=' * 80
                            print(border)
                            print(string_session)
                            print(border)
                            
                        # Save to file option
                        save_option = input("\nDo you want to save this string session to a file? (yes/no): ")
                        if save_option.lower() in ('yes', 'y'):
                            file_name = input("Enter filename (or press Enter for 'string_session.txt'): ") or "string_session.txt"
                            try:
                                with open(file_name, 'w') as f:
                                    f.write(string_session)
                                self.colored_print(f"String session saved to {file_name}", "green")
                            except Exception as e:
                                self.colored_print(f"Error saving to file: {e}", "red")
                        
                        return True
                    else:
                        self.colored_print("\nError: Missing required data in Pyrogram session", "red")
                        return False
                except Exception as e:
                    self.colored_print(f"\nError reading Pyrogram session: {e}", "red")
                    import traceback
                    traceback.print_exc()
                    return False
            except Exception as e:
                self.colored_print(f"\nError generating string session: {e}", "red")
                import traceback
                traceback.print_exc()
                return False
        
        # For other conversions, continue with the existing logic
        # Check if input file exists (for session files)
        if from_format in ["telethon", "pyrogram"]:
            if not input_path.endswith('.session') and os.path.exists(f"{input_path}.session"):
                input_path = f"{input_path}.session"
            
            if not os.path.exists(input_path):
                self.colored_print(f"\nError: Session file not found: {input_path}", "red")
                return False
                
            self.colored_print(f"\nConverting from {from_format} session file: {input_path}", "blue")
            try:
                self.show_progress("Reading session file")
                
                if from_format == "telethon":
                    session = TelegramSession.from_sqlite_session_file(input_path, self.api_id, self.api_hash)
                elif from_format == "pyrogram":
                    try:
                        from tg_converter import TelegramSession as ConverterSession
                        session = ConverterSession.from_pyrogram_session_file(input_path, self.api_id, self.api_hash)
                    except (ImportError, AttributeError):
                        # Fall back to standard method
                        session = TelegramSession.from_sqlite_session_file(input_path, self.api_id, self.api_hash)
                        
            except Exception as e:
                self.colored_print(f"\nError reading session file: {e}", "red")
                return False
        
        if not session:
            self.colored_print("\nError: Failed to create session object", "red")
            return False
        
        # Convert to the output format
        if to_format == "telethon":
            output_path = output_path or "telethon.session"
            if output_path.endswith('.session'):
                output_path = output_path[:-8]
            self.colored_print(f"\nConverting to Telethon session file: {output_path}.session", "blue")
            
            try:
                self.show_progress("Creating Telethon session")
                # This is a non-async function, so no await is needed
                result = session.make_sqlite_session_file(
                    output_path,
                    pyrogram=False
                )
                if result:
                    self.colored_print(f"\nSuccessfully created Telethon session file: {output_path}.session", "green")
                    
                    # Delete original if requested
                    if delete_original and from_format != to_format:
                        try:
                            os.remove(input_path)
                            self.colored_print(f"Original session file {input_path} deleted", "yellow")
                        except Exception as e:
                            self.colored_print(f"Error deleting original session: {e}", "red")
                    
                    return True
                else:
                    self.colored_print("\nFailed to create Telethon session file", "red")
                    return False
            except Exception as e:
                self.colored_print(f"\nError creating Telethon session: {e}", "red")
                return False
        
        elif to_format == "pyrogram":
            output_path = output_path or "pyrogram.session"
            if output_path.endswith('.session'):
                output_path = output_path[:-8]
            self.colored_print(f"\nConverting to Pyrogram session file: {output_path}.session", "blue")
            
            try:
                self.show_progress("Creating Pyrogram session")
                # This is a non-async function, so no await is needed
                result = session.make_sqlite_session_file(
                    output_path,
                    pyrogram=True
                )
                if result:
                    self.colored_print(f"\nSuccessfully created Pyrogram session file: {output_path}.session", "green")
                    
                    # Delete original if requested
                    if delete_original and from_format != to_format:
                        try:
                            os.remove(input_path)
                            self.colored_print(f"Original session file {input_path} deleted", "yellow")
                        except Exception as e:
                            self.colored_print(f"Error deleting original session: {e}", "red")
                    
                    return True
                else:
                    self.colored_print("\nFailed to create Pyrogram session file", "red")
                    return False
            except Exception as e:
                self.colored_print(f"\nError creating Pyrogram session: {e}", "red")
                return False
        
        elif to_format == "string" and from_format == "telethon":
            # Handle Telethon to string conversion
            try:
                self.show_progress("Generating string session")
                
                if HAS_TELETHON:
                    # Use Telethon's StringSession directly
                    from telethon.sessions import StringSession
                    
                    client = session.make_telethon()
                    if client:
                        string_session = StringSession.save(client.session)
                        
                        self.colored_print("\nTelethon String Session (keep this private):", "green", bold=True)
                        
                        # Display string session in a box
                        if HAS_COLORAMA:
                            border = f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}"
                            print(border)
                            print(f"{Fore.GREEN}{string_session}{Style.RESET_ALL}")
                            print(border)
                        else:
                            border = '=' * 80
                            print(border)
                            print(string_session)
                            print(border)
                            
                        # Save to file option
                        save_option = input("\nDo you want to save this string session to a file? (yes/no): ")
                        if save_option.lower() in ('yes', 'y'):
                            file_name = input("Enter filename (or press Enter for 'string_session.txt'): ") or "string_session.txt"
                            try:
                                with open(file_name, 'w') as f:
                                    f.write(string_session)
                                self.colored_print(f"String session saved to {file_name}", "green")
                            except Exception as e:
                                self.colored_print(f"Error saving to file: {e}", "red")
                        
                        return True
                    else:
                        self.colored_print("\nError: Failed to create Telethon client", "red")
                        return False
                else:
                    self.colored_print("\nError: Telethon is required for this operation", "red")
                    return False
            except Exception as e:
                self.colored_print(f"\nError generating string session: {e}", "red")
                return False
                
        return False
    
    def convert_session(self):
        """Interactive menu for session conversion"""
        self.print_header("Convert Session | VX")
        
        if not self.get_api_credentials():
            input("\nPress Enter to continue...")
            return
        
        # Get conversion details
        if HAS_COLORAMA:
            border_color = Fore.BLUE
            header_color = Fore.YELLOW + Style.BRIGHT
            option_color = Fore.CYAN
            reset = Style.RESET_ALL
        else:
            border_color = ""
            header_color = ""
            option_color = ""
            reset = ""
            
        # Source format selection
        print(f"\n{border_color}┌{'─' * 40}┐{reset}")
        print(f"{border_color}│{header_color} SELECT SOURCE FORMAT {' ' * 21}│{reset}")
        print(f"{border_color}├{'─' * 40}┤{reset}")
        print(f"{border_color}│{reset} {option_color}1.{reset} Telethon session file {' ' * 17}{border_color}│{reset}")
        print(f"{border_color}│{reset} {option_color}2.{reset} Pyrogram session file {' ' * 17}{border_color}│{reset}")
        print(f"{border_color}└{'─' * 40}┘{reset}")
        
        source_choice = input(f"\n{option_color}Enter your choice (1-2):{reset} ")
        if source_choice == "1":
            from_format = "telethon"
        elif source_choice == "2":
            from_format = "pyrogram"
        else:
            self.colored_print("\nInvalid choice", "red")
            input("\nPress Enter to return to main menu...")
            return
        
        # Get input path
        input_path = input(f"\n{option_color}Enter path to {from_format} session file:{reset} ")
        
        # Get target format
        print(f"\n{border_color}┌{'─' * 40}┐{reset}")
        print(f"{border_color}│{header_color} SELECT TARGET FORMAT {' ' * 21}│{reset}")
        print(f"{border_color}├{'─' * 40}┤{reset}")
        print(f"{border_color}│{reset} {option_color}1.{reset} Telethon session file {' ' * 17}{border_color}│{reset}")
        print(f"{border_color}│{reset} {option_color}2.{reset} Pyrogram session file {' ' * 17}{border_color}│{reset}")
        print(f"{border_color}│{reset} {option_color}3.{reset} String session (for Pyrogram) {' ' * 10}{border_color}│{reset}")
        print(f"{border_color}└{'─' * 40}┘{reset}")
        
        target_choice = input(f"\n{option_color}Enter your choice (1-3):{reset} ")
        if target_choice == "1":
            to_format = "telethon"
        elif target_choice == "2":
            to_format = "pyrogram"
        elif target_choice == "3":
            to_format = "string"
        else:
            self.colored_print("\nInvalid choice", "red")
            input("\nPress Enter to return to main menu...")
            return
        
        # Get output path if needed
        output_path = None
        if to_format in ["telethon", "pyrogram"]:
            output_path = input(f"\n{option_color}Enter output path (or press Enter for default '{to_format}.session'):{reset} ")
            if not output_path:
                output_path = f"{to_format}.session"
        
        # Ask if user wants to delete the original session
        delete_original = False
        if from_format != to_format and to_format != "string":
            delete_option = input(f"\n{option_color}Delete original session file after conversion? (yes/no):{reset} ")
            delete_original = delete_option.lower() in ('yes', 'y')
        
        # Display conversion summary
        print(f"\n{border_color}┌{'─' * 50}┐{reset}")
        print(f"{border_color}│{header_color} CONVERSION SUMMARY | VX {' ' * 27}│{reset}")
        print(f"{border_color}├{'─' * 50}┤{reset}")
        print(f"{border_color}│{reset} From Format: {option_color}{from_format.capitalize()}{' ' * (37 - len(from_format))}{border_color}│{reset}")
        print(f"{border_color}│{reset} To Format: {option_color}{to_format.capitalize()}{' ' * (39 - len(to_format))}{border_color}│{reset}")
        print(f"{border_color}│{reset} Input Path: {option_color}{input_path}{' ' * (38 - len(input_path))}{border_color}│{reset}")
        if output_path and to_format != "string":
            print(f"{border_color}│{reset} Output Path: {option_color}{output_path}{' ' * (37 - len(output_path))}{border_color}│{reset}")
        print(f"{border_color}│{reset} Delete Original: {option_color}{str(delete_original)}{' ' * (33 - len(str(delete_original)))}{border_color}│{reset}")
        print(f"{border_color}└{'─' * 50}┘{reset}")
        
        # Confirm conversion
        confirm = input(f"\n{option_color}Proceed with conversion? (yes/no):{reset} ")
        if confirm.lower() not in ('yes', 'y'):
            self.colored_print("\nConversion cancelled", "yellow")
            input("\nPress Enter to return to main menu...")
            return
        
        # Run the conversion
        self.colored_print("\nStarting conversion...", "blue")
        success = asyncio.run(self.convert_session_async(from_format, to_format, input_path, output_path, delete_original))
        
        if success:
            self.colored_print("\n✅ Conversion completed successfully!", "green", bold=True)
        else:
            self.colored_print("\n❌ Conversion failed", "red", bold=True)
            
        input("\nPress Enter to return to main menu...")
    
    def create_api_credentials_file(self):
        """Create a file to store API credentials"""
        self.print_header("Create API Credentials File")
        
        # Ask for API credentials
        try:
            api_id = input("Enter your API ID: ")
            api_id = int(api_id)  # Validate it's an integer
            api_hash = input("Enter your API Hash: ")
            
            # Ask for file path
            default_path = "telegram_api.txt"
            file_path = input(f"Enter file path to save credentials (or press Enter for '{default_path}'): ") or default_path
            
            # Create the file
            with open(file_path, "w") as f:
                f.write(f"{api_id}\n")
                f.write(f"{api_hash}\n")
                f.write("# This file contains your Telegram API credentials\n")
                f.write("# First line: API ID (integer)\n")
                f.write("# Second line: API Hash (string)\n")
                f.write(f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.colored_print(f"\nAPI credentials saved to {file_path}", "green")
            self.colored_print("You can now use the converter without entering credentials each time", "green")
            
        except ValueError:
            self.colored_print("\nError: API ID must be a number", "red")
        except Exception as e:
            self.colored_print(f"\nError creating credentials file: {e}", "red")
            
        input("\nPress Enter to return to main menu...")
    
    def run(self):
        """Main entry point for the application"""
        while True:
            choice = self.show_main_menu()
            
            if choice == "1":
                self.login_and_create_session("telethon")
            elif choice == "2":
                self.login_and_create_session("pyrogram")
            elif choice == "3":
                self.api_id = None  # Reset to force re-entering credentials
                self.api_hash = None
                self.print_header("Convert Telethon session to Pyrogram")
                if self.get_api_credentials():
                    input_path = input("\nEnter Telethon session file path: ")
                    output_path = input("\nEnter output Pyrogram session path (or press Enter for 'pyrogram.session'): ")
                    if not output_path:
                        output_path = "pyrogram.session"
                        
                    # Ask if user wants to delete the original session
                    delete_option = input("\nDelete original session file after conversion? (yes/no): ")
                    delete_original = delete_option.lower() in ('yes', 'y')
                    
                    self.colored_print("\nStarting conversion...", "blue")
                    success = asyncio.run(self.convert_session_async("telethon", "pyrogram", input_path, output_path, delete_original))
                    
                    if success:
                        self.colored_print("\nConversion completed successfully!", "green")
                    else:
                        self.colored_print("\nConversion failed", "red")
                        
                input("\nPress Enter to return to main menu...")
            elif choice == "4":
                self.api_id = None  # Reset to force re-entering credentials
                self.api_hash = None
                self.print_header("Convert Pyrogram session to Telethon")
                if self.get_api_credentials():
                    input_path = input("\nEnter Pyrogram session file path: ")
                    output_path = input("\nEnter output Telethon session path (or press Enter for 'telethon.session'): ")
                    if not output_path:
                        output_path = "telethon.session"
                        
                    # Ask if user wants to delete the original session
                    delete_option = input("\nDelete original session file after conversion? (yes/no): ")
                    delete_original = delete_option.lower() in ('yes', 'y')
                    
                    self.colored_print("\nStarting conversion...", "blue")
                    success = asyncio.run(self.convert_session_async("pyrogram", "telethon", input_path, output_path, delete_original))
                    
                    if success:
                        self.colored_print("\nConversion completed successfully!", "green")
                    else:
                        self.colored_print("\nConversion failed", "red")
                        
                input("\nPress Enter to return to main menu...")
            elif choice == "5":
                self.api_id = None  # Reset to force re-entering credentials
                self.api_hash = None
                self.print_header("Convert to String session")
                if self.get_api_credentials():
                    print("\nSelect source format:")
                    self.colored_print("1. Telethon session file", "cyan")
                    self.colored_print("2. Pyrogram session file", "cyan")
                    
                    src_choice = input("\nEnter choice (1-2): ")
                    if src_choice == "1":
                        from_format = "telethon"
                    elif src_choice == "2":
                        from_format = "pyrogram"
                    else:
                        self.colored_print("\nInvalid choice", "red")
                        input("\nPress Enter to return to main menu...")
                        continue
                        
                    input_path = input(f"\nEnter path to {from_format} session file: ")
                    asyncio.run(self.convert_session_async(from_format, "string", input_path))
                input("\nPress Enter to return to main menu...")
            elif choice == "6":
                self.check_session()
            elif choice == "7":
                self.delete_session()
            elif choice == "8":
                self.create_api_credentials_file()
            elif choice == "0":
                self.colored_print("\nExiting program...", "yellow")
                break
            else:
                self.colored_print("\nInvalid choice. Please try again.", "red")
                input("\nPress Enter to continue...")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Telegram Session Converter - A utility for managing and converting Telegram session files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the interactive converter
  python tg_client_converter.py
  
  # Create a new Telethon session (command line mode)
  python tg_client_converter.py login --type telethon --api-id 12345 --api-hash abcdef123456 --phone +1234567890
  
  # Convert Telethon session to Pyrogram
  python tg_client_converter.py convert --from telethon --to pyrogram --input telethon_session --output pyrogram_session --api-id 12345 --api-hash abcdef123456

  # Create API credentials file
  python tg_client_converter.py config
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login to Telegram and create a new session")
    login_parser.add_argument("--type", choices=["telethon", "pyrogram"], required=True, 
                             help="Type of session to create")
    login_parser.add_argument("--api-id", type=int, help="Telegram API ID")
    login_parser.add_argument("--api-hash", help="Telegram API Hash")
    login_parser.add_argument("--phone", required=True, help="Phone number in international format")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert session between formats")
    convert_parser.add_argument("--from", dest="from_format", choices=["telethon", "pyrogram"], 
                               required=True, help="Source session format")
    convert_parser.add_argument("--to", dest="to_format", choices=["telethon", "pyrogram", "string"], 
                              required=True, help="Target session format")
    convert_parser.add_argument("--input", required=True, help="Input session file path")
    convert_parser.add_argument("--output", help="Output session file path (not required for string format)")
    convert_parser.add_argument("--api-id", type=int, help="Telegram API ID")
    convert_parser.add_argument("--api-hash", help="Telegram API Hash")
    convert_parser.add_argument("--delete-original", action="store_true", 
                              help="Delete original session after conversion")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check session validity")
    check_parser.add_argument("--session", required=True, help="Session file path to check")
    check_parser.add_argument("--api-id", type=int, help="Telegram API ID")
    check_parser.add_argument("--api-hash", help="Telegram API Hash")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete session file")
    delete_parser.add_argument("--session", required=True, help="Session file path to delete")
    
    # Config command for creating API credentials file
    config_parser = subparsers.add_parser("config", help="Create API credentials file")
    config_parser.add_argument("--api-id", type=int, help="Telegram API ID")
    config_parser.add_argument("--api-hash", help="Telegram API Hash")
    config_parser.add_argument("--file", help="File path to save credentials (default: telegram_api.txt)")
    
    return parser.parse_args()

async def run_command_line(args):
    """Execute commands from command line arguments"""
    converter = TelegramSessionConverter()
    
    # Handle config command
    if args.command == "config":
        try:
            api_id = args.api_id
            api_hash = args.api_hash
            
            # If not provided as arguments, ask for them
            if not api_id:
                api_id = int(input("Enter your API ID: "))
            if not api_hash:
                api_hash = input("Enter your API Hash: ")
                
            # Get file path
            file_path = args.file or "telegram_api.txt"
            
            # Create the file
            with open(file_path, "w") as f:
                f.write(f"{api_id}\n")
                f.write(f"{api_hash}\n")
                f.write("# This file contains your Telegram API credentials\n")
                f.write("# First line: API ID (integer)\n")
                f.write("# Second line: API Hash (string)\n")
                f.write(f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"API credentials saved to {file_path}")
            print("You can now use the converter without entering credentials each time")
            return 0
        except ValueError:
            print("Error: API ID must be a number")
            return 1
        except Exception as e:
            print(f"Error creating credentials file: {e}")
            return 1
    
    # Check if API credentials are provided as args or if we need to load them
    if args.command != "delete" and (not args.api_id or not args.api_hash):
        # Try to load from file
        api_id, api_hash = read_api_credentials_from_file()
        if api_id and api_hash:
            print("Using API credentials from file")
            args.api_id = api_id
            args.api_hash = api_hash
    
    if args.command == "login":
        converter.api_id = args.api_id
        converter.api_hash = args.api_hash
        
        try:
            converter.colored_print(f"\nStarting {args.type} login process...", "blue")
            converter.show_progress("Connecting to Telegram")
            
            if args.type == "telethon":
                if not HAS_TELETHON:
                    converter.colored_print("\nError: Telethon is required for this operation. Please install it with: pip install telethon", "red")
                    return 1
                SessionManager.telethon(args.api_id, args.api_hash, args.phone)
            else:  # pyrogram
                if not HAS_PYROGRAM:
                    converter.colored_print("\nError: Pyrogram is required for this operation. Please install it with: pip install pyrogram tgcrypto", "red")
                    return 1
                SessionManager.pyrogram(args.api_id, args.api_hash, args.phone)
                
            converter.colored_print("\nSession created successfully!", "green")
            return 0
        except Exception as e:
            converter.colored_print(f"\nError creating session: {e}", "red")
            return 1
    
    elif args.command == "convert":
        converter.api_id = args.api_id
        converter.api_hash = args.api_hash
        
        output_path = args.output
        if not output_path and args.to_format != "string":
            output_path = f"{args.to_format}.session"
            
        try:
            converter.colored_print("\nStarting conversion...", "blue")
            success = await converter.convert_session_async(
                args.from_format, 
                args.to_format, 
                args.input, 
                output_path, 
                args.delete_original
            )
            
            if success:
                converter.colored_print("\nConversion completed successfully!", "green")
                return 0
            else:
                converter.colored_print("\nConversion failed", "red")
                return 1
        except Exception as e:
            converter.colored_print(f"\nError during conversion: {e}", "red")
            return 1
    
    elif args.command == "check":
        converter.api_id = args.api_id
        converter.api_hash = args.api_hash
        
        session_name = args.session
        if session_name.endswith('.session'):
            session_name = session_name.replace('.session', '')
        
        try:
            converter.colored_print("\nChecking session validity...", "blue")
            converter.show_progress("Verifying session")
            
            # Try to initialize Telegram with the session
            if not HAS_TELETHON:
                converter.colored_print("\nError: Telethon is required for this operation. Please install it with: pip install telethon", "red")
                return 1
                
            Telegram.login(args.api_id, args.api_hash, session_name)
            converter.colored_print("\nSession is valid!", "green")
            return 0
        except Exception as e:
            converter.colored_print(f"\nSession is invalid: {e}", "red")
            return 1
    
    elif args.command == "delete":
        session_path = args.session
        
        # Ensure the session file exists
        if not session_path.endswith('.session'):
            session_file = f"{session_path}.session"
        else:
            session_file = session_path
        
        if not os.path.exists(session_file):
            converter.colored_print(f"Error: Session file not found: {session_file}", "red")
            return 1
            
        # Delete the file
        try:
            os.remove(session_file)
            converter.colored_print(f"Session file {session_file} deleted successfully", "green")
            return 0
        except Exception as e:
            converter.colored_print(f"Error deleting session file: {e}", "red")
            return 1
            
    return 0

if __name__ == "__main__":
    # Check if command line arguments are provided
    if len(sys.argv) > 1:
        args = parse_arguments()
        if args.command:
            sys.exit(asyncio.run(run_command_line(args)))
    
    # Otherwise run the interactive mode
    try:
        app = TelegramSessionConverter()
        app.run()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
        sys.exit(0)