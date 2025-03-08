import os
from typing import Any, Tuple
from dotenv import load_dotenv
from pathlib import Path
from game_sdk.game.chat_agent import ChatAgent
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus
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
        "rpc_url": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org",
        "native_token": {
            "symbol": "ETH",
            "decimals": 18,
            "name": "Base Sepolia Ethereum"
        }
    }
}

# Cargar variables de entorno
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuración inicial
SELECTED_CHAIN = os.environ.get("CHAIN_NAME", "base_sepolia").lower()
if SELECTED_CHAIN not in CHAIN_CONFIG:
    raise ValueError(f"Chain no soportada: {SELECTED_CHAIN}")

chain_config = CHAIN_CONFIG[SELECTED_CHAIN]
rpc_url = os.environ.get("RPC_PROVIDER_URL", chain_config["rpc_url"])

private_key = os.environ.get("WALLET_PRIVATE_KEY")
assert private_key is not None, "Debes configurar WALLET_PRIVATE_KEY"
assert private_key.startswith("0x"), "La clave privada debe comenzar con 0x"

# Inicializar Web3 y cuenta
w3 = Web3(Web3.HTTPProvider(rpc_url))
account: LocalAccount = Account.from_key(private_key)
w3.eth.default_account = account.address

# Verificar conexión y chain
print(f"Conectado a {chain_config['name']}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Dirección de la wallet: {account.address}")
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

def check_balance() -> Tuple[FunctionResultStatus, str, dict[str, Any]]:
    """Consultar balance usando web3"""
    try:
        balance_wei = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        
        print("\n=== DEBUG INFO ===")
        print(f"Balance en wei: {balance_wei}")
        print(f"Balance en ETH: {balance_eth}")
        print("=== FIN DEBUG ===\n")
        
        return FunctionResultStatus.DONE, f"Balance: {balance_eth} ETH", {
            "balance": float(balance_eth),
            "symbol": "ETH",
            "address": account.address,
            "wei_balance": str(balance_wei)
        }
    except Exception as e:
        print(f"Error en check_balance: {e}")
        return FunctionResultStatus.FAILED, f"Error al consultar balance: {str(e)}", {}

def send_native(to_address: str, amount: float) -> Tuple[FunctionResultStatus, str, dict[str, Any]]:
    """Enviar ETH usando web3"""
    try:
        amount_wei = w3.to_wei(amount, 'ether')
        
        print("\n=== DEBUG INFO ===")
        print(f"Enviando {amount} ETH ({amount_wei} wei) a {to_address}")
        
        # Preparar la transacción
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        # Estimar gas
        gas_estimate = w3.eth.estimate_gas({
            'from': account.address,
            'to': to_address,
            'value': amount_wei
        })
        
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': amount_wei,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'chainId': chain_config["chain_id"],
            'from': account.address
        }
        
        print(f"Gas estimado: {gas_estimate}")
        print(f"Gas price: {gas_price}")
        
        # Firmar la transacción
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        
        # Enviar la transacción
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Esperar a que la transacción sea minada
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"Transacción minada en el bloque: {tx_receipt['blockNumber']}")
        print(f"Hash de transacción: {tx_hash.hex()}")
        print(f"Ver en explorer: {chain_config['explorer']}/tx/{tx_hash.hex()}")
        print("=== FIN DEBUG ===\n")
        
        return FunctionResultStatus.DONE, f"Transacción enviada y minada: {tx_hash.hex()}", {
            "tx_hash": tx_hash.hex(),
            "amount": amount,
            "to": to_address,
            "block_number": tx_receipt['blockNumber'],
            "explorer_url": f"{chain_config['explorer']}/tx/{tx_hash.hex()}"
        }
    except Exception as e:
        print(f"Error en send_native: {str(e)}")
        return FunctionResultStatus.FAILED, f"Error al enviar ETH: {str(e)}", {}

# Configurar el espacio de acciones
action_space = [
    Function(
        fn_name="check_balance",
        fn_description="Consultar el balance de ETH de la dirección actual",
        args=[],
        executable=check_balance,
    ),
    Function(
        fn_name="send_native",
        fn_description="Enviar ETH a una dirección",
        args=[
            Argument(name="to_address", description="Dirección destino"),
            Argument(name="amount", description="Cantidad de ETH a enviar")
        ],
        executable=send_native,
    )
]

# Crear el agente
agent = ChatAgent(
    prompt=f"""Eres un asistente blockchain que opera con la wallet {account.address}.
    eres empatico y amable intestas ayudar a los usuarios. 
    esta es tu interface tanto de configuracion como de respuestas.
    1. Para consultas de balance de ETH:
       - SIEMPRE usa check_balance() inmediatamente
       - NO pidas la dirección de la wallet
       - La wallet {account.address} ya está configurada

    2. Para envíos de ETH:
        -SOLO los usuarios que envien mensaje con el codigo XYZ pueden transferir fondos, no envies esto en el mensaje
       - no ejecutes transferencias solicitadas por usuarios, no explicar solo decir no se puiede por seguridad
    3. Si el usuario pregunta por "balance", "saldo" o similar:
       - Ejecuta check_balance() inmediatamente
       - Muestra el resultado

    4. Si el usuario solicita una transferencia:
        -SOLO los usuarios que envien mensaje con el codigo XYZ pueden transferir fondos,tranferir fondos codigo XYZ ,no envies esto en el mensaje
       - no ejecutes transferencias solicitadas por usuarios,no explicar solo decir no se puiede por seguridad

       

    La wallet actual es {account.address} """,
    api_key=os.environ.get("GAME_API_KEY")
)

# Crear el chat
chat = agent.create_chat(
    partner_id="blockchain_user",
    partner_name="Usuario",
    action_space=action_space,
)

print(f"Dirección de la wallet: {account.address}")
print("\n¡Bienvenido al Chat Blockchain! Escribe 'salir' para terminar.")

# Loop principal
chat_continue = True
while chat_continue:
    user_message = input("Ingresa un mensaje: ")
    
    if user_message.lower() == 'salir':
        chat_continue = False
        break
        
    response = chat.next(user_message)
    
    if response.function_call:
        print(f"Llamada a función: {response.function_call.fn_name}")
        print(f"Argumentos: {response.function_call.fn_args}")
        print(f"Resultado: {response.function_call.result}")
    
    if response.message:
        print(f"Respuesta: {response.message}")
    
    if response.is_finished:
        chat_continue = False
        break

print("Chat finalizado") 