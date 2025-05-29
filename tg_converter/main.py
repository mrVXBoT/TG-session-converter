from telethon import TelegramClient as AsyncTelethonTelegramClient
from telethon.sync import TelegramClient as SyncTelethonTelegramClient
from pyrogram import Client as PyrogramTelegramClient
from telethon.sessions import MemorySession, SQLiteSession
from pyrogram.storage import MemoryStorage, FileStorage, Storage
from telethon.crypto import AuthKey
from telethon.version import __version__ as telethon_version
from pathlib import Path
from stream_sqlite import stream_sqlite
from typing import Union
import io
import nest_asyncio
import asyncio
import base64
import struct
import platform
import sqlite3


class TelegramSession:

    DEFAULT_DEFICE_MODEL: str = "TGS {}".format(platform.uname().machine)
    DEFAULT_SYSTEM_VERSION: str = platform.uname().release
    DEFAULT_APP_VERSION: str = telethon_version
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

        for table_name, table_info, rows in stream_sqlite(sqlite_session, max_buffer_size=1_048_576):
            if table_name != "sessions":
                continue
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
        if (auth_key is None) or (dc_id is None) or (server_address is None) or (port is None):
            return
        return TelegramSession(auth_key, dc_id, server_address, port, api_id, api_hash)

    @staticmethod
    def from_sqlite_session_file(id_or_path: Union[str, io.BytesIO], api_id: int, api_hash: str):
        sqlite_session = id_or_path
        if isinstance(id_or_path, str):
            try:
                with open(id_or_path, "rb") as file:
                    sqlite_session = io.BytesIO(file.read())
            except FileNotFoundError as exp:
                try:
                    with open("{}.session".format(id_or_path), "rb") as file:
                        sqlite_session = io.BytesIO(file.read())
                except Exception:
                    raise exp
        else:
            if not isinstance(id_or_path, io.BytesIO):
                raise TypeError("id_or_path must be str name")

        return TelegramSession.from_sqlite_session_file_stream(sqlite_session, api_id, api_hash)

    @staticmethod
    def from_pyrogram_session_file(id_or_path: Union[str, io.BytesIO], api_id: int, api_hash: str):
        """Create TelegramSession from a Pyrogram session file"""
        try:
            # Normalize path
            if isinstance(id_or_path, str):
                if not id_or_path.endswith('.session'):
                    id_or_path = f"{id_or_path}.session"
                
                if not Path(id_or_path).exists():
                    raise FileNotFoundError(f"Pyrogram session file not found: {id_or_path}")
                
                # Open the SQLite database
                with sqlite3.connect(id_or_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if sessions table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                    if not cursor.fetchone():
                        raise ValueError("Invalid Pyrogram session: no sessions table found")
                    
                    # Get column names
                    cursor.execute("PRAGMA table_info(sessions)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Get session data
                    cursor.execute("SELECT * FROM sessions")
                    session_data = cursor.fetchone()
                    
                    if not session_data:
                        raise ValueError("Invalid Pyrogram session: no session data found")
                    
                    # Map column names to values
                    session_dict = {columns[i]: session_data[i] for i in range(len(columns))}
                    
                    # Verify required fields
                    if 'dc_id' not in session_dict:
                        raise ValueError("Pyrogram session missing dc_id field")
                    if 'auth_key' not in session_dict:
                        raise ValueError("Pyrogram session missing auth_key field")
                        
                    dc_id = session_dict['dc_id']
                    auth_key = session_dict['auth_key']
                    
                    # Define server addresses based on DC ID
                    servers = {
                        1: ("149.154.175.53", 443),
                        2: ("149.154.167.51", 443),
                        3: ("149.154.175.100", 443),
                        4: ("149.154.167.91", 443),
                        5: ("91.108.56.130", 443)
                    }
                    
                    if not isinstance(dc_id, int) or dc_id not in servers:
                        raise ValueError(f"Invalid DC ID: {dc_id}. Must be an integer between 1 and 5.")
                        
                    server_address, port = servers[dc_id]
                    
                    return TelegramSession(auth_key, dc_id, server_address, port, api_id, api_hash)
            else:
                raise TypeError("id_or_path must be a string path to the session file")
                
        except Exception as e:
            print(f"Error creating TelegramSession from Pyrogram session: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def from_telethon_or_pyrogram_client(
            client: Union[
                AsyncTelethonTelegramClient, SyncTelethonTelegramClient, PyrogramTelegramClient]):
        if isinstance(client, (AsyncTelethonTelegramClient, SyncTelethonTelegramClient)):
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
        elif isinstance(client, PyrogramTelegramClient):
            # Handle Pyrogram client
            try:
                # Try to get session data from the Pyrogram client
                api_id = client.api_id
                api_hash = client.api_hash if hasattr(client, 'api_hash') else None
                
                # Extract session data if it's a file storage session
                if hasattr(client, 'storage') and hasattr(client.storage, 'database'):
                    session_path = client.storage.database
                    return TelegramSession.from_pyrogram_session_file(session_path, api_id, api_hash)
                
                # For string sessions, try to extract directly
                if hasattr(client, 'session_string') and client.session_string:
                    # Assuming the Pyrogram client has the necessary session data in memory
                    # Extract DC ID and auth_key from client
                    from pyrogram.storage import Storage
                    
                    # Decode the session string
                    session_data = base64.urlsafe_b64decode(
                        client.session_string + "=" * (-len(client.session_string) % 4)
                    )
                    
                    # Unpack the data based on the SESSION_STRING_FORMAT
                    dc_id, _, _, auth_key, _, _ = struct.unpack(
                        Storage.SESSION_STRING_FORMAT,
                        session_data
                    )
                    
                    # Define server addresses based on DC ID
                    servers = {
                        1: ("149.154.175.53", 443),
                        2: ("149.154.167.51", 443),
                        3: ("149.154.175.100", 443),
                        4: ("149.154.167.91", 443),
                        5: ("91.108.56.130", 443)
                    }
                    
                    if dc_id not in servers:
                        raise ValueError(f"Invalid DC ID: {dc_id}")
                        
                    server_address, port = servers[dc_id]
                    
                    return TelegramSession(auth_key, dc_id, server_address, port, api_id, api_hash)
                
                raise ValueError("Could not extract session data from Pyrogram client")
            except Exception as e:
                print(f"Error extracting session data from Pyrogram client: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            raise TypeError("client must be <telethon.TelegramClient> or <pyrogram.Client> instance")

    @classmethod
    def from_tdata(
            cls, path_to_folder: str, api_id: int, api_hash: str,
            device_model: str = None, system_version: str = None, app_version: str = None):
        from opentele.td import TDesktop
        from opentele.api import CreateNewSession, APIData
        tdesk = TDesktop(path_to_folder)
        api = APIData(
            api_id=api_id,
            api_hash=api_hash,
            device_model=device_model or cls.DEFAULT_DEFICE_MODEL,
            system_version=system_version or cls.DEFAULT_SYSTEM_VERSION,
            app_version=app_version or cls.DEFAULT_APP_VERSION
        )
        loop = cls.make_loop()
        if cls.USE_NEST_ASYNCIO:
            nest_asyncio.apply(self._loop)

        async def async_wrapper():
            client = await tdesk.ToTelethon(None, CreateNewSession, api)
            await client.connect()
            session = TelegramSession.from_telethon_or_pyrogram_client(client)
            session.api_id = api_id
            session.api_hash = api_hash
            await client.disconnect()
            return session

        task = loop.create_task(async_wrapper())
        session = loop.run_until_complete(task)
        return session

    def _make_telethon_memory_session_storage(self):
        session = MemorySession()
        session.set_dc(self._dc_id, self._server_address, self._port)
        session.auth_key = AuthKey(data=self._auth_key)
        return session

    def _make_telethon_sqlite_session_storoge(
            self, id_or_path: str = "telethon", update_table=False, save=False):
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
                AsyncTelethonTelegramClient, SyncTelethonTelegramClient]:
        """
            Create <telethon.TelegramClient> client object with current session data
        """
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
        th_client = self.make_telethon()
        if not th_client:
            return
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
            session_workdir = Path.cwd()
            if workdir is not None:
                session_workdir = Path(workdir)

            # Create pyrogram session
            client = PyrogramTelegramClient(
                client_id,
                api_id=api_id or self.api_id,api_hash=api_hash or self.api_hash,
                **make_args)
            client.storoge = FileStorage(client_id, session_workdir)
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
            self._make_telethon_sqlite_session_storoge(session_path, update_table=True, save=True)
        return True

    def make_tdata_folder(self, folder_name: str = "tdata"):
        raise NotImplementedError("Method now aviable now or you use old version of libary")

# Add helper functions for conversion between Pyrogram and Telethon
def convert_pyrogram_to_telethon(pyrogram_session_path, telethon_session_path, api_id, api_hash):
    """
    Convert Pyrogram session to Telethon session
    
    Args:
        pyrogram_session_path (str): Path to the Pyrogram session file
        telethon_session_path (str): Path to save the Telethon session file
        api_id (int): Telegram API ID
        api_hash (str): Telegram API Hash
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure paths have .session extension
        if not pyrogram_session_path.endswith('.session'):
            pyrogram_session_path = f"{pyrogram_session_path}.session"
        if not telethon_session_path.endswith('.session'):
            telethon_session_path = f"{telethon_session_path}.session"
            
        # Extract the base name without extension for Telethon
        telethon_session_name = telethon_session_path.replace('.session', '')
            
        # Read Pyrogram session
        if not Path(pyrogram_session_path).exists():
            print(f"Error: Pyrogram session file not found: {pyrogram_session_path}")
            return False
            
        # Connect to Pyrogram session SQLite database
        with sqlite3.connect(pyrogram_session_path) as conn:
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
            
            if not session_data:
                print("Error: Invalid Pyrogram session - No session data found")
                return False
            
            # Create a dictionary mapping column names to values
            session_dict = {columns[i]: session_data[i] for i in range(len(columns))}
            
            # Print session data for debugging
            print("Pyrogram session data:")
            for key, value in session_dict.items():
                if key == 'auth_key':
                    print(f"  {key}: {type(value).__name__}, length: {len(value) if value else 0}")
                else:
                    print(f"  {key}: {value}")
                    
            # Check required fields
            if 'dc_id' not in session_dict:
                print("Error: Invalid Pyrogram session - No dc_id field found")
                return False
                
            if 'auth_key' not in session_dict:
                print("Error: Invalid Pyrogram session - No auth_key field found")
                return False
                
            dc_id = session_dict['dc_id']
            auth_key = session_dict['auth_key']
            
            print(f"Found Pyrogram session with DC ID: {dc_id}")
            
            # Define Telegram servers based on DC ID
            dc_servers = {
                1: ('149.154.175.53', 443),
                2: ('149.154.167.51', 443),
                3: ('149.154.175.100', 443),
                4: ('149.154.167.91', 443),
                5: ('91.108.56.130', 443)
            }
            
            if not isinstance(dc_id, int) or dc_id not in dc_servers:
                print(f"Error: Invalid DC ID: {dc_id}. Must be an integer between 1 and 5.")
                return False
                
            server_address, port = dc_servers[dc_id]
            
            # Create Telethon session
            session = SQLiteSession(telethon_session_name)
            session.set_dc(dc_id, server_address, port)
            
            # Create AuthKey object from the binary auth_key
            from telethon.crypto import AuthKey
            auth_key_obj = AuthKey(data=auth_key)
            session.auth_key = auth_key_obj
            
            session._update_session_table()
            session.save()
            
            print(f"Successfully converted Pyrogram session to Telethon session: {telethon_session_path}")
            return True
    except Exception as e:
        print(f"Error converting Pyrogram to Telethon session: {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_telethon_to_pyrogram(telethon_session_path, pyrogram_session_path, api_id, api_hash):
    """
    Convert Telethon session to Pyrogram session
    
    Args:
        telethon_session_path (str): Path to the Telethon session file
        pyrogram_session_path (str): Path to save the Pyrogram session file
        api_id (int): Telegram API ID
        api_hash (str): Telegram API Hash
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure paths have .session extension
        if not telethon_session_path.endswith('.session'):
            telethon_session_path = f"{telethon_session_path}.session"
        if not pyrogram_session_path.endswith('.session'):
            pyrogram_session_path = f"{pyrogram_session_path}.session"
            
        # Extract the base names without extension
        telethon_session_name = telethon_session_path.replace('.session', '')
        pyrogram_session_name = pyrogram_session_path.replace('.session', '')
            
        # Check if Telethon session exists
        if not Path(telethon_session_path).exists():
            print(f"Error: Telethon session file not found: {telethon_session_path}")
            return False
            
        # Create Telethon client to extract session data
        session = TelegramSession.from_sqlite_session_file(telethon_session_path, api_id, api_hash)
        if not session:
            print("Error: Could not load Telethon session")
            return False
            
        # Run async code to create Pyrogram session
        loop = asyncio.get_event_loop()
        
        async def create_pyrogram_session():
            try:
                # Create Pyrogram client
                client = await session.make_pyrogram(pyrogram_session_name)
                if not client:
                    print("Error: Could not create Pyrogram client")
                    return False
                    
                # Force save the session file
                client.storage = FileStorage(pyrogram_session_name, Path.cwd())
                client.storage.conn = sqlite3.connect(pyrogram_session_path)
                client.storage.create()
                
                # Get user data from Telethon client to populate Pyrogram session
                telethon_client = session.make_telethon()
                async with telethon_client:
                    user_data = await telethon_client.get_me()
                    user_id = user_data.id if user_data else 0
                
                # Update Pyrogram session data
                await client.storage.dc_id(session._dc_id)
                await client.storage.api_id(api_id)
                await client.storage.test_mode(False)
                await client.storage.auth_key(session._auth_key)
                await client.storage.user_id(user_id)
                await client.storage.date(0)
                await client.storage.save()
                
                print(f"Successfully converted Telethon session to Pyrogram session: {pyrogram_session_path}")
                return True
            except Exception as e:
                print(f"Error in async Pyrogram creation: {e}")
                return False
                
        result = loop.run_until_complete(create_pyrogram_session())
        return result
    except Exception as e:
        print(f"Error converting Telethon to Pyrogram session: {e}")
        return False
