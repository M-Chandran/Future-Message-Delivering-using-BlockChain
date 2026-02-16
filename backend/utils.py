import os
import tempfile
from cryptography.fernet import Fernet

# CSV file paths
USERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'storage', 'users.csv')
MESSAGES_CSV = os.path.join(os.path.dirname(__file__), '..', 'storage', 'messages.csv')

# Configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip'}

# Encryption key file path


ENCRYPTION_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'storage', '.encryption_key')

def load_or_generate_encryption_key():
    """Load existing encryption key or generate and save a new one"""
    # First check environment variable
    env_key = os.getenv('ENCRYPTION_KEY')
    if env_key:
        return env_key
    
    # Try to load from file
    if os.path.exists(ENCRYPTION_KEY_FILE):
        try:
            with open(ENCRYPTION_KEY_FILE, 'r') as f:
                return f.read().strip()
        except Exception:
            pass
    
    # Generate new key and save to file
    new_key = Fernet.generate_key().decode()
    try:
        # Ensure storage directory exists
        os.makedirs(os.path.dirname(ENCRYPTION_KEY_FILE), exist_ok=True)
        with open(ENCRYPTION_KEY_FILE, 'w') as f:
            f.write(new_key)
    except Exception as e:
        print(f"Warning: Could not save encryption key to file: {e}")
    
    return new_key

# Global encryption key for consistency - load from file or generate once
ENCRYPTION_KEY = load_or_generate_encryption_key()


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Get file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'image'
    elif ext in ['pdf', 'doc', 'docx']:
        return 'document'
    else:
        return 'file'

def encrypt_data(data, encryption_key=None):
    """Encrypt data using Fernet"""
    if encryption_key is None:
        encryption_key = ENCRYPTION_KEY
    cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    return cipher.encrypt(data)

def decrypt_data(encrypted_data, encryption_key=None):
    """Decrypt data using Fernet"""
    if encryption_key is None:
        encryption_key = ENCRYPTION_KEY
    cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    return cipher.decrypt(encrypted_data)

def upload_to_ipfs(data, filename, ipfs_client=None):
    """Upload data to IPFS"""
    try:
        if not ipfs_client:
            # Import here to avoid circular imports
            try:
                import ipfshttpclient  # type: ignore
                ipfs_client = ipfshttpclient.connect('/ip4/localhost/tcp/5001/http')
            except ImportError:
                print("Warning: ipfshttpclient not installed. IPFS upload skipped.")
                return None
            except Exception as e:
                print(f"Warning: Could not connect to IPFS: {e}")
                return None

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data if isinstance(data, bytes) else data.encode())
            temp_file_path = temp_file.name

        try:
            # Add file to IPFS
            res = ipfs_client.add(temp_file_path, filename=filename)
            return res['Hash']
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    except Exception as e:
        print(f"Error uploading to IPFS: {e}")
        return None


def download_from_ipfs(ipfs_hash, ipfs_client=None):
    """Download data from IPFS"""
    try:
        if not ipfs_client:
            # Import here to avoid circular imports
            try:
                import ipfshttpclient  # type: ignore
                ipfs_client = ipfshttpclient.connect('/ip4/localhost/tcp/5001/http')
            except ImportError:
                print("Warning: ipfshttpclient not installed. IPFS download skipped.")
                return None
            except Exception as e:
                print(f"Warning: Could not connect to IPFS: {e}")
                return None

        # Get data from IPFS
        data = ipfs_client.cat(ipfs_hash)
        return data
    except Exception as e:
        print(f"Error downloading from IPFS: {e}")
        return None
