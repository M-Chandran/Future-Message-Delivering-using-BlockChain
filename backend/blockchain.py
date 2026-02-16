import hashlib
import requests
import json
from time import time
from datetime import datetime
from web3 import Web3
import os

# Blockchain persistence file
BLOCKCHAIN_FILE = os.path.join(os.path.dirname(__file__), '..', 'storage', 'blockchain.json')

class Block:

    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions  # List of time-locked messages
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty):
        while self.hash[:difficulty] != '0' * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()

class SmartContract:
    def __init__(self, contract_address, abi):
        self.contract_address = contract_address
        self.abi = abi

class AdvancedBlockchain:
    def __init__(self, difficulty=4, ethereum_node_url=None):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = difficulty
        self.smart_contracts = {}
        self.nodes = set()
        self.ethereum_integration = None

        if ethereum_node_url:
            self.connect_to_ethereum(ethereum_node_url)

        # Try to load existing blockchain from file
        if not self.load_blockchain():
            self.create_genesis_block()


    def connect_to_ethereum(self, node_url):
        self.ethereum_integration = Web3(Web3.HTTPProvider(node_url))
        if not self.ethereum_integration.is_connected():
            raise Exception("Failed to connect to Ethereum node")

    def create_genesis_block(self):
        genesis_block = Block(0, time(), [], "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        self.pending_transactions.append(transaction)

    def mine_pending_transactions(self):
        if not self.pending_transactions:
            return False

        block = Block(
            len(self.chain),
            time(),
            self.pending_transactions.copy(),
            self.get_latest_block().hash
        )
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []
        
        # Save blockchain to file after mining
        self.save_blockchain()
        return True


    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def add_node(self, address):
        self.nodes.add(address)

    def resolve_conflicts(self):
        """Consensus algorithm to resolve chain conflicts"""
        longest_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            try:
                response = requests.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    if length > max_length and self.is_valid_chain(chain):
                        max_length = length
                        longest_chain = chain
            except:
                pass

        if longest_chain:
            self.chain = longest_chain
            return True

        return False

    def deploy_smart_contract(self, contract_code, contract_name):
        """Deploy a smart contract to the blockchain"""
        if self.ethereum_integration:
            # Deploy to Ethereum
            compiled_contract = self.ethereum_integration.eth.contract(abi=[], bytecode=contract_code)
            tx_hash = compiled_contract.constructor().transact()
            tx_receipt = self.ethereum_integration.eth.wait_for_transaction_receipt(tx_hash)
            contract_address = tx_receipt.contractAddress
            self.smart_contracts[contract_name] = SmartContract(contract_address, [])
            return contract_address
        else:
            # Store in custom blockchain
            contract_hash = hashlib.sha256(contract_code.encode()).hexdigest()
            self.smart_contracts[contract_name] = SmartContract(contract_hash, contract_code)
            return contract_hash

    def execute_smart_contract(self, contract_name, function_name, *args):
        """Execute a smart contract function"""
        if contract_name not in self.smart_contracts:
            raise Exception("Contract not found")

        contract = self.smart_contracts[contract_name]
        if self.ethereum_integration:
            # Execute on Ethereum
            contract_instance = self.ethereum_integration.eth.contract(
                address=contract.contract_address,
                abi=contract.abi
            )
            return getattr(contract_instance.functions, function_name)(*args).call()
        else:
            # Simulate execution in custom blockchain
            return f"Executed {function_name} on {contract_name} with args {args}"

    def get_message_by_id(self, message_id):
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.get('id') == message_id:
                    return transaction
        return None

    def can_reveal_message(self, message_id):
        transaction = self.get_message_by_id(message_id)
        if not transaction:
            return False

        unlock_time = datetime.fromisoformat(transaction['unlock_time'])
        return datetime.now() >= unlock_time

    def get_all_messages_for_user(self, user_id):
        messages = []
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.get('user_id') == user_id:
                    messages.append(transaction)
        return messages

    def get_blockchain_stats(self):
        """Get advanced blockchain statistics"""
        total_blocks = len(self.chain)
        total_transactions = sum(len(block.transactions) for block in self.chain)
        average_block_time = 0
        if total_blocks > 1:
            timestamps = [block.timestamp for block in self.chain]
            average_block_time = (timestamps[-1] - timestamps[0]) / (total_blocks - 1)

        return {
            'total_blocks': total_blocks,
            'total_transactions': total_transactions,
            'average_block_time': average_block_time,
            'difficulty': self.difficulty,
            'nodes': len(self.nodes),
            'smart_contracts': len(self.smart_contracts),
            'ethereum_connected': self.ethereum_integration is not None and self.ethereum_integration.is_connected()
        }

    def save_blockchain(self):
        """Save blockchain to JSON file for persistence"""
        try:
            # Ensure storage directory exists
            os.makedirs(os.path.dirname(BLOCKCHAIN_FILE), exist_ok=True)
            
            # Convert chain to serializable format
            chain_data = []
            for block in self.chain:
                chain_data.append({
                    'index': block.index,
                    'timestamp': block.timestamp,
                    'transactions': block.transactions,
                    'previous_hash': block.previous_hash,
                    'nonce': block.nonce,
                    'hash': block.hash
                })
            
            data = {
                'chain': chain_data,
                'pending_transactions': self.pending_transactions,
                'difficulty': self.difficulty,
                'smart_contracts': {k: {'address': v.contract_address, 'abi': v.abi} 
                                   for k, v in self.smart_contracts.items()},
                'nodes': list(self.nodes)
            }
            
            with open(BLOCKCHAIN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving blockchain: {e}")
            return False

    def load_blockchain(self):
        """Load blockchain from JSON file"""
        try:
            if not os.path.exists(BLOCKCHAIN_FILE):
                return False
            
            with open(BLOCKCHAIN_FILE, 'r') as f:
                data = json.load(f)
            
            # Restore chain
            self.chain = []
            for block_data in data.get('chain', []):
                block = Block(
                    block_data['index'],
                    block_data['timestamp'],
                    block_data['transactions'],
                    block_data['previous_hash'],
                    block_data['nonce']
                )
                block.hash = block_data['hash']
                self.chain.append(block)
            
            # Restore other data
            self.pending_transactions = data.get('pending_transactions', [])
            self.difficulty = data.get('difficulty', 4)
            self.nodes = set(data.get('nodes', []))
            
            # Restore smart contracts
            for name, contract_data in data.get('smart_contracts', {}).items():
                self.smart_contracts[name] = SmartContract(
                    contract_data['address'],
                    contract_data['abi']
                )
            
            print(f"Blockchain loaded from file: {len(self.chain)} blocks")
            return True
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            return False

# Global blockchain instance
blockchain = AdvancedBlockchain()
