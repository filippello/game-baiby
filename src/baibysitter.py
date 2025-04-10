import httpx
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional, List
from game_sdk.game.custom_types import FunctionResultStatus, AgentMessage
from game_sdk.game.chat_agent import Chat

class Babysitter:
    def __init__(self, api_url: str):
        self.api_url = api_url
        
    def validate_transaction(
        self, 
        from_address: str,
        to_address: str, 
        amount: float,
        chat: Chat,
    ) -> Tuple[bool, str]:
        """
        Validates a transaction by consulting the external API
        """
        messages = chat.get_history()
        
        conversation = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation.append(f"{role}: {msg['content']}")
        
        reason = "\n".join(conversation)
        
        tx_data = {
            "safeAddress": from_address,
            "erc20TokenAddress": "ETH",
            "reason": reason,
            "transactions": [{
                "to": to_address,
                "data": "",
                "value": str(Decimal(str(amount)) * Decimal('1000000000000000000'))
            }]
        }
        
        try:
            response = httpx.post(
                self.api_url, 
                json=tx_data, 
                timeout=30.0
            )
            response_data = response.json()
            message = response_data.get('message', '')
            is_approved = 'APPROVED' in message
            return is_approved, message
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"

def wrap_send_native(
    original_fn,
    babysitter: Babysitter,
    wallet_address: str,
    chat: Chat,
) -> callable:
    def wrapped_send_native(to_address: str, amount: float) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        print(f"\n💰 Transaction details:")
        print(f"   From: {wallet_address}")
        print(f"   To: {to_address}")
        print(f"   Amount: {amount} ETH")
        
        try:
            is_valid, message = babysitter.validate_transaction(
                from_address=wallet_address,
                to_address=to_address,
                amount=amount,
                chat=chat
            )
            
            if not is_valid:
                return FunctionResultStatus.FAILED, f"Transaction rejected: {message}", {}
            
            return original_fn(to_address, amount)
            
        except Exception as e:
            return FunctionResultStatus.FAILED, f"Execution error: {str(e)}", {}
        
    return wrapped_send_native 