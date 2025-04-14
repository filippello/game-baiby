# Baibysitter Plugin for G.A.M.E - Documentation

![Image](https://github.com/user-attachments/assets/81ad7e35-5ed7-4555-b8c5-73cd5f8b9834)

## Description

Baibysitter is a plugin designed to monitor and validate blockchain transactions within conversations with AI agents.
It acts as a security layer that compares the intent expressed in the chat with the actual blockchain transaction, using an API and a cluster of sentinels to detect potential financial losses.

## Other infraestructure

this is the other repository for the baibysitter api:

- https://github.com/baibysitter/baibysitter-api

## Installation

```
# Install from local directory
pip install -e plugins/baibysitter

# Dependencies will be installed automatically:
# - game-sdk
# - web3
# - python-dotenv
# - httpx
```

## Configuration

Set up the environment variables in the `.env` file:

```
GAME_API_KEY=your_game_api_key
API_URL=api.baibysitter.xyz:8000
WALLET_PRIVATE_KEY=your_private_key
```

## Main Components

### 1. Baibysitter Class

The main class responsible for validating transactions. The `validate_transaction` method compares the chat intent with the transaction details by querying an external API.

### 2. Chat History

The chat history is managed using two main methods:

- `save_message` in `api_v2.py`: Saves individual messages to the history.
- `get_history` in `chat_agent.py`: Retrieves the full conversation history.

## Usage Example

The file `chat_blockchain.py` demonstrates the full implementation:

- Initializes the chat agent with security configuration.
- Sets up the action space with wrapped validation functions.
- Handles transactions with pre-validation.
- Maintains conversation history for context.

### Key Functions:

```
# Initialize Baibysitter
babysitter = Babysitter(api_url=os.environ.get("API_URL"))

# Wrap send function
wrapped_send = wrap_send_native(
    send_native,
    babysitter,
    wallet_address=account.address,
    chat=chat
)
```

## Validation Flow

1. User requests a transaction in the chat.
2. The system captures the chat intent and context.
3. Baibysitter validates the transaction against the external API.
4. If approved, the transaction is executed.
5. The result is saved to the conversation history.

## Security

The plugin implements multiple layers of security:

- Intent vs action validation.
- Full conversation logging.
- External transaction verification.
