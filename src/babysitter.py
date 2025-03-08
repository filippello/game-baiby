import httpx
import asyncio
import os
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional
from game_sdk.game.custom_types import FunctionResultStatus

class Babysitter:
    def __init__(self, api_url: str):
        self.api_url = api_url
        print(f"🔍 Babysitter inicializado con API URL: {self.api_url}")
        
    def validate_transaction(
        self, 
        from_address: str,
        to_address: str, 
        amount: float,
        conversation_history: list,
    ) -> Tuple[bool, str]:
        """
        Valida una transacción consultando la API externa (versión sincrónica)
        """
        print(f"\n🔄 Iniciando validación de transacción:")
        print(f"   De: {from_address}")
        print(f"   Para: {to_address}")
        print(f"   Monto: {amount} ETH")
        print(f"   Historial de conversación: {conversation_history}")
        
        # Convertir el amount a wei usando Decimal para evitar errores de precisión
        amount_in_wei = str(Decimal(str(amount)) * Decimal('1000000000000000000'))
        
        tx_data = {
            "safeAddress": from_address,
            "erc20TokenAddress": "ETH",
            "reason": "\n".join(conversation_history) if conversation_history else "No conversation history",
            "transactions": [{
                "to": to_address,
                "data": "",
                "value": amount_in_wei
            }]
        }
        
        print(f"\n📤 Enviando datos a la API: {tx_data}")
        
        try:
            print(f"🌐 Conectando a {self.api_url}...")
            response = httpx.post(
                self.api_url, 
                json=tx_data, 
                timeout=30.0
            )
            print(f"📥 Código de respuesta HTTP: {response.status_code}")
            
            response_data = response.json()
            print(f"📝 Respuesta completa de la API: {response_data}")
            
            message = response_data.get('message', '')
            is_approved = 'APPROVED' in message
            print(f"✉️ Mensaje de la API: {message}")
            print(f"✅ ¿Está aprobada? {is_approved}")
            
            return is_approved, message
                
        except Exception as e:
            print(f"❌ Error en la validación: {str(e)}")
            print(f"❌ Tipo de error: {type(e)}")
            import traceback
            print(f"❌ Traceback completo: {traceback.format_exc()}")
            return False, f"Error en la validación: {str(e)}"

def wrap_send_native(
    original_fn,
    babysitter: Babysitter,
    wallet_address: str,
    conversation_history: Optional[list] = None
) -> callable:
    """
    Envuelve la función original de envío con la validación del babysitter
    """
    def wrapped_send_native(to_address: str, amount: float) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        print("\n🔒 Iniciando wrapped_send_native:")
        print(f"   Wallet: {wallet_address}")
        print(f"   Destino: {to_address}")
        print(f"   Monto: {amount} ETH")
        
        try:
            # Validar primero con el babysitter
            is_valid, message = babysitter.validate_transaction(
                from_address=wallet_address,
                to_address=to_address,
                amount=amount,
                conversation_history=conversation_history or []
            )
            
            if not is_valid:
                print(f"❌ Transacción rechazada por babysitter: {message}")
                return FunctionResultStatus.FAILED, f"Transacción rechazada: {message}", {}
            
            print("✅ Transacción aprobada por babysitter, procediendo con el envío...")
            # Si pasa la validación, ejecutar la función original
            return original_fn(to_address, amount)
            
        except Exception as e:
            print(f"❌ Error en wrapped_send_native: {str(e)}")
            import traceback
            print(f"❌ Traceback completo: {traceback.format_exc()}")
            return FunctionResultStatus.FAILED, f"Error en la ejecución: {str(e)}", {}
        
    return wrapped_send_native 