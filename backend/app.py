# Increase CSV field size limit for large encrypted files - MUST be set before importing csv
import csv
import sys
# Set to maximum possible value to handle large encrypted messages
csv.field_size_limit(sys.maxsize)


from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import io
import threading
import logging
from datetime import datetime

from cryptography.fernet import Fernet
from web3 import Web3
import json
import hashlib
from PIL import Image
import tempfile
from dotenv import load_dotenv
from blockchain import AdvancedBlockchain
from google_drive import GoogleDriveStorage
from utils import encrypt_data, decrypt_data, ENCRYPTION_KEY

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create upload folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Encryption key - use fixed key for consistency

# File paths
USERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'storage', 'users.csv')
MESSAGES_CSV = os.path.join(os.path.dirname(__file__), '..', 'storage', 'messages.csv')

# Thread locks for CSV operations
csv_locks = {
    'users': threading.Lock(),
    'messages': threading.Lock()
}

# Initialize services
blockchain = AdvancedBlockchain()
google_drive = GoogleDriveStorage()

# Web3 integration (optional)
INFURA_URL = os.getenv('INFURA_URL')
if INFURA_URL:
    try:
        w3 = Web3(Web3.HTTPProvider(INFURA_URL))
        if w3.is_connected():
            logger.info("Connected to Ethereum network")
        else:
            logger.warning("Failed to connect to Ethereum network")
            w3 = None
    except Exception as e:
        logger.error(f"Ethereum connection error: {e}")
        w3 = None
else:
    w3 = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'image'
    elif ext in ['pdf', 'doc', 'docx', 'txt']:
        return 'document'
    else:
        return 'file'

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Get all messages for the user
        all_messages = []
        with csv_locks['messages']:
            if os.path.exists(MESSAGES_CSV):
                with open(MESSAGES_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    all_messages = list(reader)

        # Filter messages for current user - be more flexible to match both numeric ID and wallet address
        current_user_id = session.get('user_id')
        user_wallet = session.get('wallet_address') or session.get('user_id')
        
        # Also try to match by numeric ID if user_id is a wallet address, or vice versa
        messages = []
        for row in all_messages:
            # Check by user_id (exact match)
            if row.get('user_id') == current_user_id:
                messages.append(row)
            # Check by receiver_wallet
            elif row.get('receiver_wallet') == user_wallet:
                messages.append(row)
            # Check if current_user_id is numeric and matches numeric user_id in CSV
            elif current_user_id and current_user_id.isdigit() and row.get('user_id') == current_user_id:
                messages.append(row)
            # Check if user_id in CSV is numeric and matches current session user_id
            elif row.get('user_id') and row.get('user_id').isdigit() and str(row.get('user_id')) == str(current_user_id):
                messages.append(row)

        # Auto-reveal messages that are ready
        updated = False
        for row in messages:
            try:
                reveal_time = datetime.fromisoformat(row['unlock_time'])
                can_reveal = datetime.now() >= reveal_time
                if can_reveal and row['status'] == 'locked':
                    row['status'] = 'revealed'
                    updated = True
                    logger.info(f"Auto-revealed message {row['id']} for user {session['user_id']}")
            except ValueError as e:
                logger.error(f"Error parsing unlock_time for message {row['id']}: {e}")
                continue

        # Save updated messages back to CSV if any were updated
        if updated:
            with csv_locks['messages']:
                with open(MESSAGES_CSV, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['id', 'user_id', 'receiver_wallet', 'ipfs_hash', 'message_type', 'unlock_time', 'created_time', 'status', 'encrypted_message', 'tx_hash'])
                    writer.writeheader()
                    writer.writerows(all_messages)

        total_messages = len(messages)
        locked_count = sum(1 for message in messages if message.get('status') == 'locked')
        unlocked_count = sum(1 for message in messages if message.get('status') == 'unlocked')
        revealed_count = sum(1 for message in messages if message.get('status') == 'revealed')

        return render_template('dashboard.html', messages=messages, user_name=session.get('user_name', 'User'), total_messages=total_messages, unlocked_count=unlocked_count, locked_count=locked_count, revealed_count=revealed_count)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', messages=[], user_name=session.get('user_name', 'User'), total_messages=0, unlocked_count=0, locked_count=0, revealed_count=0, error='Failed to load messages')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        logger.info(f"Login attempt for email: {email}")

        with csv_locks['users']:
            if not os.path.exists(USERS_CSV):
                logger.error(f"Users CSV not found at: {USERS_CSV}")
                return render_template('login.html', error='User database not found')

            with open(USERS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logger.info(f"Checking row: email={row.get('email')}, password_hash present={bool(row.get('password_hash'))}")
                    if row['email'].strip() == email and check_password_hash(row['password_hash'], password):
                        session['user_id'] = row['id']
                        session['user_name'] = row['name']
                        session['wallet_address'] = row.get('wallet_address', '')
                        logger.info(f"Login successful for user: {row['name']}")
                        return redirect(url_for('dashboard'))



        logger.info("Login failed: Invalid credentials")
        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        wallet_address = request.form.get('wallet_address', '')

        with csv_locks['users']:
            # Check if user already exists
            if os.path.exists(USERS_CSV):
                with open(USERS_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['email'] == email:
                            return render_template('register.html', error='Email already exists')

            # Get next user ID
            user_id = 1
            if os.path.exists(USERS_CSV):
                with open(USERS_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if len(rows) > 1:
                        user_id = int(rows[-1][0]) + 1

            # Hash password
            password_hash = generate_password_hash(password)

            # Save to CSV
            with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([user_id, name, email, password_hash, wallet_address])

        session['user_id'] = wallet_address or str(user_id)
        session['user_name'] = name
        session['wallet_address'] = wallet_address
        return redirect(url_for('dashboard'))



    return render_template('register.html')



@app.route('/create_message', methods=['GET', 'POST'])
def create_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            message_type = request.form.get('message_type', 'text')
            reveal_time_str = request.form['reveal_time']

            # Parse reveal time
            reveal_time = datetime.strptime(reveal_time_str, '%Y-%m-%dT%H:%M')

            # Validate reveal time is in the future
            if reveal_time <= datetime.now():
                return render_template('create_message.html', error='Reveal time must be in the future')

            # Convert to ISO format for storage
            reveal_time_str = reveal_time.isoformat()

            # Get next message ID
            message_id = 1
            with csv_locks['messages']:
                if os.path.exists(MESSAGES_CSV):
                    with open(MESSAGES_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        if len(rows) > 1:
                            message_id = int(rows[-1][0]) + 1

            encrypted_content = ""
            content_hash = ""
            ipfs_hash = ""

            if message_type == 'text':
                # Handle text message
                message = request.form.get('message', '').strip()
                if not message:
                    return render_template('create_message.html', error='Message content is required')

                encrypted_content = encrypt_data(message.encode())
                content_hash = hashlib.sha256(message.encode()).hexdigest()
            else:
                # Handle file upload
                if 'file' not in request.files:
                    return render_template('create_message.html', error='No file uploaded')

                file = request.files['file']
                if file.filename == '':
                    return render_template('create_message.html', error='No file selected')

                if not allowed_file(file.filename):
                    return render_template('create_message.html', error='File type not allowed')

                if file.content_length > MAX_FILE_SIZE:
                    return render_template('create_message.html', error='File too large (max 10MB)')

                # Read file content
                file_content = file.read()

                # Encrypt file content
                encrypted_content = encrypt_data(file_content)

                # Store locally (Google Drive upload disabled for now)
                ipfs_hash = ''  # No Google Drive upload
                content_hash = hashlib.sha256(file_content).hexdigest()

            # Create transaction for blockchain
            transaction = {
                'id': message_id,
                'user_id': session['user_id'],
                'message_hash': content_hash,
                'unlock_time': reveal_time_str,
                'timestamp': datetime.now().isoformat(),
                'message_type': message_type,
                'ipfs_hash': ipfs_hash
            }

            # Add transaction to blockchain
            blockchain.add_transaction(transaction)

            # Mine the block
            blockchain.mine_pending_transactions()

            # Get block hash as tx_hash
            latest_block = blockchain.get_latest_block()
            tx_hash = latest_block.hash

            # Save to CSV
            with csv_locks['messages']:
                with open(MESSAGES_CSV, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([message_id, session['user_id'], session['wallet_address'] or session['user_id'], ipfs_hash, message_type, reveal_time_str, datetime.now().isoformat(), 'locked', encrypted_content.decode(), tx_hash])

            logger.info(f"Message {message_id} created successfully, redirecting to dashboard")
            flash(f'Message #{message_id} created successfully! It will be unlockable at {reveal_time_str}', 'success')
            return redirect(url_for('dashboard'))



        except ValueError as e:
            return render_template('create_message.html', error='Invalid date/time format')
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return render_template('create_message.html', error='Failed to create message. Please try again.')

    return render_template('create_message.html')

@app.route('/reveal_message/<int:message_id>')
def reveal_message(message_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with csv_locks['messages']:
        if not os.path.exists(MESSAGES_CSV):
            return render_template('reveal_message.html', error='Message database not found')

        with open(MESSAGES_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['id'] == str(message_id) and row['user_id'] == session['user_id']:
                    try:
                        reveal_time = datetime.fromisoformat(row['unlock_time'])
                        if datetime.now() >= reveal_time:
                            message_type = row.get('message_type', 'text')
                            ipfs_hash = row.get('ipfs_hash', '')

                            if message_type == 'text':
                                # Decrypt text message and display on page
                                decrypted_message = decrypt_data(row['encrypted_message'].encode()).decode()
                                return render_template('reveal_message.html', message=decrypted_message, message_type='text')
                            else:
                                # For files, decrypt and display/download
                                try:
                                    if ipfs_hash:
                                        encrypted_data = google_drive.download_file(ipfs_hash)
                                        decrypted_content = decrypt_data(encrypted_data)
                                    else:
                                        # Fallback to stored encrypted content
                                        encrypted_data = row['encrypted_message'].encode()
                                        decrypted_content = decrypt_data(encrypted_data)

                                    # Determine file type and handle accordingly
                                    if message_type == 'image':
                                        # For images, display inline with base64 encoding
                                        import base64
                                        image_base64 = base64.b64encode(decrypted_content).decode('utf-8')
                                        return render_template('reveal_message.html',
                                                             message_type='image',
                                                             image_data=image_base64,
                                                             message_id=message_id)
                                    else:
                                        # For documents, provide download link
                                        return render_template('reveal_message.html',
                                                             message_type='document',
                                                             file_data=decrypted_content,
                                                             message_id=message_id,
                                                             original_filename=f"revealed_message_{message_id}")
                                except Exception as e:
                                    logger.error(f"Content retrieval failed: {e}")
                                    return render_template('reveal_message.html', error='Failed to retrieve message content')
                        else:
                            return render_template('reveal_message.html', error='Message is still locked')
                    except ValueError as e:
                        logger.error(f"Error parsing reveal_time for message {message_id}: {e}")
                        return render_template('reveal_message.html', error='Invalid message data')

    return render_template('reveal_message.html', error='Message not found')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# API Endpoints

@app.route('/api/messages', methods=['POST'])
def create_message_api():
    """Create a new time-locked message"""
    try:
        # Get data from request
        data = request.get_json()
        wallet_address = data.get('wallet_address')
        receiver_wallet = data.get('receiver_wallet')
        unlock_time = data.get('unlock_time')
        message_type = data.get('message_type', 'text')
        content = data.get('content', '')

        if not receiver_wallet or not unlock_time:
            return jsonify({'error': 'Receiver wallet and unlock time required'}), 400

        # Encrypt content
        encrypted_content = encrypt_data(content.encode())

        # Store locally (Google Drive upload disabled for now)
        ipfs_hash = ''

        # Create blockchain transaction
        transaction = {
            'wallet_address': wallet_address,
            'receiver_wallet': receiver_wallet,
            'ipfs_hash': ipfs_hash,
            'message_type': message_type,
            'unlock_time': unlock_time,
            'timestamp': datetime.now().isoformat()
        }

        # Add to blockchain
        blockchain.add_transaction(transaction)
        blockchain.mine_pending_transactions()

        # Get transaction hash
        latest_block = blockchain.get_latest_block()
        tx_hash = latest_block.hash

        # Save to local storage
        with csv_locks['messages']:
            # Get next message ID
            message_id = 1
            if os.path.exists(MESSAGES_CSV):
                with open(MESSAGES_CSV, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if len(rows) > 1:
                        message_id = int(rows[-1][0]) + 1

            with open(MESSAGES_CSV, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    message_id,
                    wallet_address,
                    receiver_wallet,
                    ipfs_hash,
                    message_type,
                    unlock_time,
                    datetime.now().isoformat(),
                    'locked'
                ])

        return jsonify({
            'success': True,
            'message_id': message_id,
            'tx_hash': tx_hash,
            'ipfs_hash': ipfs_hash
        })

    except Exception as e:
        logger.error(f"API create message error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages', methods=['GET'])
def get_messages_api():
    """Get messages for the authenticated user"""
    try:
        wallet_address = request.args.get('wallet_address') or session.get('wallet_address')
        if not wallet_address:
            return jsonify({'error': 'Wallet address required'}), 400

        messages = []

        # Get from local storage
        if os.path.exists(MESSAGES_CSV):
            with open(MESSAGES_CSV, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Show messages where user is either sender or receiver
                    if row.get('user_id') == str(wallet_address) or row.get('receiver_wallet') == wallet_address:
                        unlock_timestamp = int(datetime.fromisoformat(row['unlock_time'].replace('Z', '+00:00')).timestamp())
                        messages.append({
                            'id': int(row['id']),
                            'sender': row.get('user_id', ''),  # Use user_id as sender
                            'receiver': row['receiver_wallet'],
                            'ipfs_hash': row['ipfs_hash'],
                            'message_type': row['message_type'],
                            'unlock_time': unlock_timestamp,
                            'created_time': int(datetime.fromisoformat(row['created_time']).timestamp()),
                            'is_revealed': row['status'] == 'revealed',
                            'can_reveal': datetime.now().timestamp() >= unlock_timestamp and row['status'] != 'revealed'
                        })

        return jsonify({'messages': messages})

    except Exception as e:
        logger.error(f"API get messages error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<int:message_id>/reveal', methods=['POST'])
def reveal_message_api(message_id):
    """Reveal a message"""
    try:
        # Get JSON data - handle empty body gracefully
        data = {}
        if request.is_json:
            try:
                data = request.get_json() or {}
            except Exception:
                pass
        
        wallet_address = data.get('wallet_address') or session.get('wallet_address') or session.get('user_id')


        if not wallet_address:
            return jsonify({'error': 'Authentication required'}), 400

        logger.info(f"Reveal request for message {message_id} by wallet {wallet_address}")

        # Get encrypted content and update status
        messages = []
        message_found = False
        decrypted_data = None
        message_type = None

        with csv_locks['messages']:
            if not os.path.exists(MESSAGES_CSV):
                return jsonify({'error': 'Message database not found'}), 404

            with open(MESSAGES_CSV, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logger.info(f"Checking message {row['id']} with user_id {row.get('user_id')} and receiver_wallet {row.get('receiver_wallet')}")
                    if int(row['id']) == message_id:
                        # Check if user can access this message (receiver or sender for web app)
                        if (row.get('receiver_wallet') == wallet_address or
                            (session.get('user_id') and row.get('user_id') == session.get('user_id'))):
                            logger.info(f"Message {message_id} belongs to wallet {wallet_address}")
                            message_found = True
                            message_type = row.get('message_type', 'text')

                            # If already revealed, just return the content without error
                            already_revealed = (row['status'] == 'revealed')


                            # Check reveal time
                            try:
                                reveal_time = datetime.fromisoformat(row['unlock_time'])
                                if datetime.now() < reveal_time:
                                    return jsonify({'error': 'Message is still locked'}), 403
                            except ValueError:
                                return jsonify({'error': 'Invalid unlock time format'}), 500

                            # Decrypt content for both text and files
                            try:
                                if row.get('ipfs_hash'):
                                    # Download from Google Drive
                                    encrypted_data = google_drive.download_file(row['ipfs_hash'])
                                    decrypted_data = decrypt_data(encrypted_data)
                                else:
                                    # Fallback to stored encrypted content
                                    encrypted_data = row['encrypted_message'].encode()
                                    decrypted_data = decrypt_data(encrypted_data)
                            except Exception as e:
                                logger.error(f"Content retrieval failed: {e}")
                                return jsonify({'error': 'Failed to retrieve message content'}), 500

                            # Update status
                            row['status'] = 'revealed'

                    messages.append(row)

            if not message_found:
                logger.error(f"Message {message_id} not found or access denied for wallet {wallet_address}")
                return jsonify({'error': 'Message not found'}), 404

            # Write back updated messages
            with open(MESSAGES_CSV, 'w', newline='') as f:
                if messages:
                    writer = csv.DictWriter(f, fieldnames=['id', 'user_id', 'receiver_wallet', 'ipfs_hash', 'message_type', 'unlock_time', 'created_time', 'status', 'encrypted_message', 'tx_hash'])
                    writer.writeheader()
                    writer.writerows(messages)

        # Handle different content types properly
        if message_type == 'text':
            # Text content can be decoded as UTF-8
            content = decrypted_data.decode() if isinstance(decrypted_data, bytes) else str(decrypted_data)
        else:
            # Binary content (files, images) should be base64 encoded for JSON transport
            import base64
            content = base64.b64encode(decrypted_data).decode('utf-8') if isinstance(decrypted_data, bytes) else decrypted_data

        return jsonify({
            'success': True,
            'content': content,
            'message_type': message_type,
            'is_binary': message_type != 'text',
            'already_revealed': already_revealed
        })



    except Exception as e:
        logger.error(f"Reveal API error: {e}")
        return jsonify({'error': 'Failed to reveal message'}), 500


@app.route('/api/messages/<int:message_id>/delete', methods=['DELETE'])
def delete_message_api(message_id):
    """Delete a message"""
    try:
        # Get JSON data - handle empty body gracefully
        data = {}
        if request.is_json:
            try:
                data = request.get_json() or {}
            except Exception:
                pass
        
        wallet_address = data.get('wallet_address') or session.get('wallet_address') or session.get('user_id')
        if not wallet_address:
            logger.error("Delete failed: No authentication")
            return jsonify({'error': 'Authentication required'}), 400


        logger.info(f"Delete request for message {message_id} by wallet {wallet_address}")
        logger.info(f"Session user_id: {session.get('user_id')}, wallet_address: {session.get('wallet_address')}")

        messages = []
        message_found = False
        message_to_delete = None

        with csv_locks['messages']:
            if not os.path.exists(MESSAGES_CSV):
                logger.error(f"Delete failed: Messages CSV not found at {MESSAGES_CSV}")
                return jsonify({'error': 'Message database not found'}), 404

            with open(MESSAGES_CSV, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logger.info(f"Checking message {row['id']} with user_id {row.get('user_id')}, receiver_wallet {row.get('receiver_wallet')}")
                    if int(row['id']) == message_id:
                        # Check if user owns this message (can delete if sender or receiver)
                        user_id_match = str(row.get('user_id')) == str(wallet_address)
                        receiver_match = row.get('receiver_wallet') == wallet_address
                        session_match = session.get('user_id') and str(row.get('user_id')) == str(session.get('user_id'))
                        
                        logger.info(f"Message {message_id} checks: user_id_match={user_id_match}, receiver_match={receiver_match}, session_match={session_match}")
                        
                        if (user_id_match or receiver_match or session_match):
                            logger.info(f"Message {message_id} belongs to wallet {wallet_address} - DELETING")
                            message_found = True
                            message_to_delete = row
                            continue  # Skip adding this row to messages list
                        else:
                            logger.warning(f"Message {message_id} does not belong to wallet {wallet_address} (owner: {row.get('user_id')}, receiver: {row.get('receiver_wallet')})")
                    messages.append(row)

            if not message_found:
                logger.error(f"Message {message_id} not found or access denied for wallet {wallet_address}")
                return jsonify({'error': 'Message not found or access denied'}), 404


            # If message has a file in Google Drive, we could optionally delete it here
            # For now, we'll just remove the database entry

            # Write back updated messages (without the deleted one)
            with open(MESSAGES_CSV, 'w', newline='', encoding='utf-8') as f:
                if messages:
                    writer = csv.DictWriter(f, fieldnames=messages[0].keys())
                    writer.writeheader()
                    writer.writerows(messages)
                else:
                    # If no messages left, write header only
                    writer = csv.writer(f)
                    writer.writerow(['id', 'user_id', 'receiver_wallet', 'ipfs_hash', 'message_type', 'unlock_time', 'created_time', 'status', 'encrypted_message', 'tx_hash'])

        return jsonify({'success': True, 'message': 'Message deleted successfully'})


    except Exception as e:
        logger.error(f"Delete API error: {e}")
        return jsonify({'error': 'Failed to delete message'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file for message creation"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    if file.content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large'}), 400

    # Read file data
    file_data = file.read()

    # Encrypt file
    encrypted_data = encrypt_data(file_data)

    # Upload to Google Drive
    upload_result = google_drive.upload_file(encrypted_data, secure_filename(file.filename))
    file_id = upload_result['file_id']

    return jsonify({
        'success': True,
        'ipfs_hash': file_id,
        'message_type': get_file_type(file.filename)
    })

@app.route('/api/messages/<int:message_id>/status', methods=['PUT'])
def update_message_status_api(message_id):
    """Update message status (e.g., from locked to unlocked/revealed)"""
    try:
        # Get JSON data - handle empty body gracefully
        data = {}
        if request.is_json:
            try:
                data = request.get_json() or {}
            except Exception:
                pass
        
        wallet_address = data.get('wallet_address') or session.get('wallet_address') or session.get('user_id')
        if not wallet_address:
            return jsonify({'error': 'Authentication required'}), 400
        
        new_status = data.get('status', 'unlocked')
        
        messages = []
        message_found = False
        
        with csv_locks['messages']:
            if not os.path.exists(MESSAGES_CSV):
                return jsonify({'error': 'Message database not found'}), 404

            with open(MESSAGES_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row['id']) == message_id:
                        # Check if user owns this message
                        if (row.get('user_id') == wallet_address or 
                            row.get('receiver_wallet') == wallet_address or
                            (session.get('user_id') and row.get('user_id') == session.get('user_id'))):
                            row['status'] = new_status
                            message_found = True
                    messages.append(row)

            if not message_found:
                return jsonify({'error': 'Message not found or access denied'}), 404

            # Write back updated messages
            with open(MESSAGES_CSV, 'w', newline='', encoding='utf-8') as f:
                if messages:
                    writer = csv.DictWriter(f, fieldnames=['id', 'user_id', 'receiver_wallet', 'ipfs_hash', 'message_type', 'unlock_time', 'created_time', 'status', 'encrypted_message', 'tx_hash'])
                    writer.writeheader()
                    writer.writerows(messages)

        return jsonify({'success': True, 'message': f'Status updated to {new_status}'})

    except Exception as e:
        logger.error(f"Status update API error: {e}")
        return jsonify({'error': 'Failed to update message status'}), 500


@app.route('/api/blockchain/timestamp', methods=['GET'])
def get_blockchain_timestamp():

    """Get current blockchain timestamp"""
    try:
        if w3 and w3.is_connected():
            timestamp = w3.eth.get_block('latest')['timestamp']
        else:
            timestamp = int(datetime.now().timestamp())

        return jsonify({'timestamp': timestamp})
    except Exception as e:
        logger.error(f"Blockchain timestamp error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<message_id>', methods=['GET'])
def download_file(message_id):
    """Download and decrypt file by message ID"""
    try:
        # Find the message by ID
        with csv_locks['messages']:
            if not os.path.exists(MESSAGES_CSV):
                return jsonify({'error': 'Message database not found'}), 404

            with open(MESSAGES_CSV, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(message_id):
                        # Check if user can access this message
                        if row['user_id'] == session.get('user_id'):
                            message_type = row.get('message_type', 'text')
                            ipfs_hash = row.get('ipfs_hash', '')

                            # Decrypt content
                            try:
                                if ipfs_hash:
                                    encrypted_data = google_drive.download_file(ipfs_hash)
                                    decrypted_data = decrypt_data(encrypted_data)
                                else:
                                    # Fallback to stored encrypted content
                                    encrypted_data = row['encrypted_message'].encode()
                                    decrypted_data = decrypt_data(encrypted_data)

                                # Determine filename based on message type
                                if message_type == 'image':
                                    filename = f"revealed_image_{message_id}.png"
                                elif message_type == 'document':
                                    filename = f"revealed_document_{message_id}.pdf"
                                else:
                                    filename = f"revealed_file_{message_id}"

                                # Return file
                                return send_file(
                                    io.BytesIO(decrypted_data),
                                    as_attachment=True,
                                    download_name=filename
                                )
                            except Exception as e:
                                logger.error(f"Content retrieval failed: {e}")
                                return jsonify({'error': 'Failed to retrieve message content'}), 500
                        else:
                            return jsonify({'error': 'Access denied'}), 403

        return jsonify({'error': 'Message not found'}), 404

    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

