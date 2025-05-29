import sqlite3, sys, re  # noqa E401
import base64
import struct
import os
import time
from pathlib import Path

try:
    from telethon import functions, errors as telethon_errors
    from telethon.sync import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.tl.types import Channel
except ModuleNotFoundError:
    print(
        "\n―― ⚠️ The Telethon library is not installed."
        "\n―― Please install it by running: `pip install telethon`"
    )
    sys.exit(1)
except ImportError as ie:
    print(
        f"\n―― ⚠️ {ie}"
        "\n―― Try updating Telethon by running: `pip install --upgrade telethon`"
    )
    sys.exit(1)


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


class SessionManager:
    """
    Create Telegram sessions using Telethon or Pyrogram.

    `[YouTube] How to Create Telegram Sessions <https://www.youtube.com/watch?v=-2vWERIXXZU>`_
    """

    @staticmethod
    def telethon(api_id: int = None, api_hash: str = None, phone: str = None) -> None:
        """
        Create Telethon Sessions.

        `API ID & API HASH <https://my.telegram.org/auth>`_ |
        `What are Sessions? <https://docs.telethon.dev/en/stable/concepts/sessions.html#what-are-sessions>`_

        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param phone: Phone number in international format. If you want to generate a string session,
               enter your telethon session file name instead.
        """

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
            f"\n―― ✨ STRING SESSION: {StringSession.save(client.session)}"  # noqa
        )

        _handle_user_actions(client)

    @staticmethod
    def pyrogram(api_id: int = None, api_hash: str = None, phone: str = None) -> None:
        """
        Create Pyrogram Sessions.

        `API ID & API HASH <https://my.telegram.org/auth>`_ |
        `More about Pyrogram <https://docs.pyrogram.org/api/client/>`_
        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param phone: Phone number in international format. If you want to generate a string session,
               enter your pyrogram session file name instead.
        """
        try:
            from pyrogram import Client, filters, errors as pyrogram_errors
        except ModuleNotFoundError:
            print("\n―― ⚠️ The Pyrogram library is not installed.")
            print("―― Please install it by running: `pip install pyrogram`")
            sys.exit(1)

        _show_warning()

        user_api_id = api_id or int(input("Enter your API ID: "))
        user_api_hash = api_hash or input("Enter your API HASH: ")
        user_phone = phone or input("Enter your phone number (e.g. +1234567890): ")

        try:
            client = Client(user_phone, user_api_id, user_api_hash, phone_number=user_phone)
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


class Telegram:
    """
    Interact with Telegram.

    `[YouTube] Login to Telegram Using a Session File or String Session <https://www.youtube.com/watch?v=T2qQfX7kjgI>`_
    """

    @staticmethod
    def login(api_id: int = None, api_hash: str = None, session_name: str = None) -> None:
        """
        Login to Telegram using Telethon session file.
        :param api_id: Telegram API ID.
        :param api_hash: Telegram API hash.
        :param session_name: Your Telethon session file name
        """
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
                with client:
                    client.run_until_disconnected()
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


def convert_session(input_path, output_path, from_format="telethon", to_format="pyrogram", api_id=None, api_hash=None):
    """
    Convert between Telethon and Pyrogram session formats
    
    Args:
        input_path (str): Path to the input session file
        output_path (str): Path to save the output session file
        from_format (str): Source format ("telethon" or "pyrogram")
        to_format (str): Target format ("telethon" or "pyrogram")
        api_id (int): Telegram API ID
        api_hash (str): Telegram API Hash
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate arguments
    if from_format not in ["telethon", "pyrogram"] or to_format not in ["telethon", "pyrogram", "string"]:
        print(f"Error: Invalid format specified. from_format must be 'telethon' or 'pyrogram', "
              f"to_format must be 'telethon', 'pyrogram', or 'string'")
        return False
        
    if from_format == to_format and to_format != "string":
        print(f"Warning: Source and target formats are the same ({from_format})")
        
    # Check if input file exists
    if not input_path.endswith('.session'):
        input_path = f"{input_path}.session"
    if not os.path.exists(input_path):
        print(f"Error: Session file not found: {input_path}")
        return False
        
    # Ensure output path has .session extension
    if not output_path.endswith('.session') and to_format != "string":
        output_path = f"{output_path}.session"
        
    # Get API credentials if not provided
    if not api_id or not api_hash:
        api_id = int(input("Enter your API ID: "))
        api_hash = input("Enter your API HASH: ")
        
    # Handle different conversion scenarios
    if from_format == "telethon" and to_format == "pyrogram":
        return _telethon_to_pyrogram(input_path, output_path, api_id, api_hash)
    elif from_format == "pyrogram" and to_format == "telethon":
        return _pyrogram_to_telethon(input_path, output_path, api_id, api_hash)
    elif from_format == "telethon" and to_format == "string":
        return _telethon_to_string(input_path, api_id, api_hash)
    elif from_format == "pyrogram" and to_format == "string":
        return _pyrogram_to_string(input_path, api_id, api_hash)
    else:
        print("Unsupported conversion combination")
        return False

def _telethon_to_pyrogram(telethon_path, pyrogram_path, api_id, api_hash):
    """Convert Telethon session to Pyrogram session"""
    try:
        # Import required Pyrogram modules
        try:
            from pyrogram import Client
            from pyrogram.storage import FileStorage
        except ImportError:
            print("Pyrogram is required for this conversion. Install with: pip install pyrogram")
            return False
            
        # Extract data from Telethon session
        conn = sqlite3.connect(telethon_path)
        cursor = conn.cursor()
        cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
        session_data = cursor.fetchone()
        conn.close()
        
        if not session_data:
            print("Invalid Telethon session: No session data found")
            return False
            
        dc_id, server_address, port, auth_key = session_data
        
        # Create temporary client to get user ID
        client = TelegramClient(StringSession(), api_id, api_hash)
        client.session.set_dc(dc_id, server_address, port)
        client.session.auth_key = auth_key  # Set the auth key directly
        
        # Connect and get user ID
        user_id = 0
        try:
            client.connect()
            if client.is_user_authorized():
                me = client.get_me()
                user_id = me.id
        except Exception as e:
            print(f"Warning: Could not get user ID: {e}")
        finally:
            client.disconnect()
        
        # Create Pyrogram client and session
        pyrogram_client = Client(
            name=os.path.basename(pyrogram_path).replace('.session', ''),
            api_id=api_id,
            api_hash=api_hash,
            workdir=os.path.dirname(pyrogram_path) or '.'
        )
        
        # Create storage and set data
        storage = FileStorage(os.path.basename(pyrogram_path).replace('.session', ''), 
                              Path(os.path.dirname(pyrogram_path) or '.'))
                              
        # Connect to SQLite database
        storage.conn = sqlite3.connect(pyrogram_path)
        storage.create()
        
        # Set session data in the database
        cursor = storage.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, dc_id, False, auth_key, int(time.time()), user_id, False)
        )
        storage.conn.commit()
        storage.conn.close()
        
        print(f"Successfully converted Telethon session to Pyrogram: {pyrogram_path}")
        return True
    except Exception as e:
        print(f"Error converting Telethon to Pyrogram session: {e}")
        return False

def _pyrogram_to_telethon(pyrogram_path, telethon_path, api_id, api_hash):
    """Convert Pyrogram session to Telethon session"""
    try:
        # Extract data from Pyrogram session
        conn = sqlite3.connect(pyrogram_path)
        cursor = conn.cursor()
        
        # First, check if the sessions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cursor.fetchone():
            print(f"Error: Invalid Pyrogram session file - no sessions table found")
            return False
        
        # Get column names
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get session data
        cursor.execute("SELECT * FROM sessions")
        session_data = cursor.fetchone()
        conn.close()
        
        if not session_data:
            print("Invalid Pyrogram session: No session data found")
            return False
            
        # Create a dictionary mapping column names to values
        session_dict = {columns[i]: session_data[i] for i in range(len(columns))}
        
        # Debug output
        print("Pyrogram session data:")
        for key, value in session_dict.items():
            if key == 'auth_key':
                print(f"  {key}: {type(value).__name__}, length: {len(value) if value else 0}")
            else:
                print(f"  {key}: {value}")
        
        # Check required fields
        if 'dc_id' not in session_dict:
            print("Error: Pyrogram session missing dc_id field")
            return False
        if 'auth_key' not in session_dict:
            print("Error: Pyrogram session missing auth_key field")
            return False
            
        dc_id = session_dict['dc_id']
        auth_key = session_dict['auth_key']
        
        print(f"Found Pyrogram session with DC ID: {dc_id}")
        
        # Define server addresses based on DC ID
        servers = {
            1: ("149.154.175.53", 443),
            2: ("149.154.167.51", 443),
            3: ("149.154.175.100", 443),
            4: ("149.154.167.91", 443),
            5: ("91.108.56.130", 443)
        }
        
        if not isinstance(dc_id, int) or dc_id not in servers:
            print(f"Error: Invalid DC ID: {dc_id}. Must be an integer between 1 and 5.")
            return False
            
        server_address, port = servers[dc_id]
        
        # Create Telethon session
        from telethon.sessions import SQLiteSession  
        from telethon.crypto import AuthKey
        
        session = SQLiteSession(telethon_path.replace('.session', ''))
        session.set_dc(dc_id, server_address, port)
        session.auth_key = AuthKey(data=auth_key)
        session._update_session_table()
        session.save()
        
        print(f"Successfully converted Pyrogram session to Telethon: {telethon_path}")
        return True
    except Exception as e:
        print(f"Error converting Pyrogram to Telethon session: {e}")
        import traceback
        traceback.print_exc()
        return False

def _telethon_to_string(telethon_path, api_id, api_hash):
    """Convert Telethon session to string session"""
    try:
        # Create a client with the session file
        client = TelegramClient(telethon_path.replace('.session', ''), api_id, api_hash)
        
        # Connect if needed
        connected = False
        try:
            client.connect()
            connected = True
        except:
            pass
            
        # Get string session
        string_session = StringSession.save(client.session)
        
        # Disconnect if we connected
        if connected:
            client.disconnect()
            
        print(f"Telethon String Session: {string_session}")
        return True
    except Exception as e:
        print(f"Error converting Telethon to string session: {e}")
        return False

def _pyrogram_to_string(pyrogram_path, api_id, api_hash):
    """Convert Pyrogram session to string session"""
    try:
        # Import required Pyrogram modules
        try:
            from pyrogram import Client
        except ImportError:
            print("Pyrogram is required for this conversion. Install with: pip install pyrogram")
            return False
            
        # Create a client with the session file
        client = Client(
            name=pyrogram_path.replace('.session', ''),
            api_id=api_id,
            api_hash=api_hash,
            workdir=os.path.dirname(pyrogram_path) or '.'
        )
        
        # Get string session
        try:
            client.start()
            string_session = client.export_session_string()
            client.stop()
        except:
            # Try to read directly from the file
            conn = sqlite3.connect(pyrogram_path)
            cursor = conn.cursor()
            cursor.execute("SELECT dc_id, api_id, test_mode, auth_key, user_id, is_bot FROM sessions")
            session_data = cursor.fetchone()
            conn.close()
            
            if not session_data:
                print("Invalid Pyrogram session: No session data found")
                return False
                
            dc_id, _, test_mode, auth_key, user_id, is_bot = session_data
            
            try:
                from pyrogram.storage import Storage
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
            except ImportError:
                print("Pyrogram Storage class could not be imported")
                return False
                
        print(f"Pyrogram String Session: {string_session}")
        return True
    except Exception as e:
        print(f"Error converting Pyrogram to string session: {e}")
        return False


if __name__ == "__main__":
    commands = {
        "--telethon": SessionManager.telethon,
        "--pyrogram": SessionManager.pyrogram,
        "--login": Telegram.login,
    }

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        action = commands.get(cmd)
        if action:
            action()
        else:
            print(f"\n―― ❌  Unknown command: `{cmd}`\n"
                  f"――  Supported commands: {', '.join(commands.keys())}\n"
                  f"――  Example: `python telegram.py --login`\n")
