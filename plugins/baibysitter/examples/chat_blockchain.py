import os
from typing import Any, Tuple, Dict
from dotenv import load_dotenv
from pathlib import Path
from baibysitter.baibysitter_game_sdk.chat_agent import ChatAgent
from baibysitter.baibysitter_game_sdk.custom_types import Argument, Function, FunctionResultStatus
from baibysitter.baibysitter_game_sdk.baibysitter import Babysitter, wrap_send_native
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

# Importaciones de goat
from goat_adapters.langchain import get_on_chain_tools
from goat_plugins.erc20.token import USDC
from goat_plugins.erc20 import erc20, ERC20PluginOptions
from goat_wallets.evm import send_eth
from goat_wallets.web3 import Web3EVMWalletClient

# Configuración de chains
CHAIN_CONFIG = {
    "base_sepolia": {
        "name": "Base Sepolia",
        "chain_id": 84532,
        "rpc_url": "https://multi-quaint-leaf.zksync-sepolia.quiknode.pro/da0d39e9df88697276020a15c017af0764d66327",
        "explorer": "https://sepolia.explorer.zksync.io",
        "native_token": {
            "symbol": "ETH",
            "decimals": 18,
            "name": "zk Sepolia"
        }
    }
}

# Cargar variables de entorno
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuración inicial
SELECTED_CHAIN = os.environ.get("CHAIN_NAME", "base_sepolia").lower()
if SELECTED_CHAIN not in CHAIN_CONFIG:
    raise ValueError(f"Chain no supported: {SELECTED_CHAIN}")

chain_config = CHAIN_CONFIG[SELECTED_CHAIN]
rpc_url = os.environ.get("RPC_PROVIDER_URL", chain_config["rpc_url"])

private_key = os.environ.get("WALLET_PRIVATE_KEY")
assert private_key is not None, "WALLET_PRIVATE_KEY must be configured"
assert private_key.startswith("0x"), "Private key must start with 0x"

# Inicializar Web3 y cuenta
w3 = Web3(Web3.HTTPProvider(rpc_url))
account: LocalAccount = Account.from_key(private_key)
w3.eth.default_account = account.address

# Verificar conexión y chain
print(f"Connected to {chain_config['name']}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Wallet address: {account.address}")
print(f"Explorer: {chain_config['explorer']}")

# Inicializar wallet y herramientas
wallet = Web3EVMWalletClient(w3)
tools = get_on_chain_tools(
    wallet=wallet,
    plugins=[
        send_eth(),
        erc20(options=ERC20PluginOptions(tokens=[USDC]))
    ]
)

# Después de inicializar Web3 y la cuenta
babysitter = Babysitter(api_url=os.environ.get("API_URL"))

# Mantener un historial de la conversación
conversation_history = []

# Modificar la función que maneja los mensajes para guardar el historial
def handle_message(message: str):
    conversation_history.append(message)
    # ... resto del código de manejo de mensajes ...

def check_balance() -> Tuple[FunctionResultStatus, str, dict[str, Any]]:
    """Check balance using web3"""
    try:
        balance_wei = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        
        print("\n=== DEBUG INFO ===")
        print(f"Balance in wei: {balance_wei}")
        print(f"Balance in ETH: {balance_eth}")
        print("=== END DEBUG ===\n")
        
        return FunctionResultStatus.DONE, f"Balance: {balance_eth} ETH", {
            "balance": float(balance_eth),
            "symbol": "ETH",
            "address": account.address,
            "wei_balance": str(balance_wei)
        }
    except Exception as e:
        print(f"Error in check_balance: {e}")
        return FunctionResultStatus.FAILED, f"Error checking balance: {str(e)}", {}

def send_native(to_address: str, amount: float) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
    """Send ETH to an address"""
    try:
        print(f"\n💰 Starting send_native:")
        print(f"   From: {account.address}")
        print(f"   To: {to_address}")
        print(f"   Amount: {amount} ETH")
        
        # Check balance
        balance = w3.eth.get_balance(account.address)
        print(f"   Current balance: {w3.from_wei(balance, 'ether')} ETH")
        
        # Verify sufficient funds
        if balance < w3.to_wei(amount, 'ether'):
            print("❌ Insufficient funds")
            return FunctionResultStatus.FAILED, "Insufficient funds", {}

        # Build transaction
        transaction = {
            'to': to_address,
            'value': w3.to_wei(amount, 'ether'),
            'gas': 300000,  # Increased gas limit for ZkSync
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        }
        print(f"   Transaction built: {transaction}")

        # Estimate gas first
        estimated_gas = w3.eth.estimate_gas({
            'from': account.address,
            'to': to_address,
            'value': w3.to_wei(amount, 'ether')
        })
        gas_limit = max(estimated_gas * 2, 300000)  # Use at least 300000 or double the estimate

        # Send transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"   Transaction hash: {tx_hash.hex()}")
        
        return FunctionResultStatus.DONE, f"Transaction sent successfully. Hash: {tx_hash.hex()}", {"tx_hash": tx_hash.hex()}
        
    except Exception as e:
        print(f"❌ Error in send_native: {str(e)}")
        import traceback
        print(f"❌ Complete traceback: {traceback.format_exc()}")
        return FunctionResultStatus.FAILED, f"Transaction error: {str(e)}", {}

# Crear el agente
agent = ChatAgent(
    prompt=f"""You are a blockchain assistant operating with wallet {account.address}.
    You are empathetic and friendly, always trying to help users.
    This is your interface for both configuration and responses.
    1. For eth balance queries:
       - ALWAYS use check_balance() immediately
       - DO NOT ask for the wallet address
       - Wallet {account.address} is already configured
    2. If user asks about "balance" or similar:
       - Execute check_balance() immediately
       - Show the result

    

    if warining comes from firewall review with warningemoticons
    The current wallet is {account.address}""",
    api_key=os.environ.get("GAME_API_KEY")
)

# Crear el chat
chat = agent.create_chat(
    partner_id="blockchain_user",
    partner_name="User",
)

# Luego configuramos el action_space con los mensajes del chat
action_space = [
    Function(
        fn_name="check_balance",
        fn_description="Check ETH balance of current address",
        args=[],
        executable=check_balance,
    ),
    Function(
        fn_name="send_native",
        fn_description="Send ETH to an address",
        args=[
            Argument(name="to_address", description="Destination address"),
            Argument(name="amount", description="Amount of ETH to send")
        ],
        executable=wrap_send_native(
            send_native,
            babysitter,
            wallet_address=account.address,
            chat=chat  # Pass complete chat object
        ),
    )
]

# Actualizamos el chat con el action_space
chat.action_space = {f.fn_name: f for f in action_space}

print(f"Wallet address: {account.address}")
print("\nWelcome to Blockchain Chat! Type 'exit' to end.")

# Loop principal
chat_continue = True
while chat_continue:
    user_message = input("Enter a message: ")
    
    if user_message.lower() == 'exit':
        chat_continue = False
        break
        
    response = chat.next(user_message)
    
    if response.function_call:
        print(f"Function call: {response.function_call.fn_name}")
        print(f"Arguments: {response.function_call.fn_args}")
        print(f"Result: {response.function_call.result}")
    
    if response.message:
        print(f"Response: {response.message}")
    
    if response.is_finished:
        chat_continue = False
        break

print("Chat ended") 