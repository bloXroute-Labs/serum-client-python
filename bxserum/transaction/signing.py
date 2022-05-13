import os
import base58
import base64
from solana.keypair import Keypair
from solana.transaction import Transaction

def sign_tx(unsigned_tx_base64: str) -> str:
    # get base58 encoded private key
    pkey_str = os.getenv("PRIVATE_KEY")
    if pkey_str == None:
        raise EnvironmentError("env variable `PRIVATE_KEY` not set")

    # convert b58 private key string to a keypair
    pkey_bytes_base58 = bytes(pkey_str, encoding="utf-8")
    pkey_bytes = base58.b58decode(pkey_bytes_base58)
    key_pair = Keypair.from_secret_key(pkey_bytes)

    sign_tx_with_private_key(unsigned_tx_base64, key_pair)


def sign_tx_with_private_key(unsigned_tx_base64: str, key_pair: Keypair):
    # convert base64 transaction string to a transaction
    tx_bytes_base64 = bytes(unsigned_tx_base64, encoding="utf-8")
    tx_bytes = base64.decodebytes(tx_bytes_base64)
    tx = Transaction.deserialize(tx_bytes)

    # sign transaction using keypair
    _sign_tx(tx, key_pair)

    tx_base_64_bytes = base64.b64encode(tx.serialize())
    return tx_base_64_bytes.decode("utf-8")

def _sign_tx(tx: Transaction, key_pair: Keypair):
    signatures_required = tx.compile_message().header.num_required_signatures
    signatures_present = len(tx.signatures)
    if signatures_present != signatures_required:
        raise Exception(f"transaction requires {signatures_required} signatures and has {signatures_present} signatures")
    _replace_zero_signature(tx, key_pair)

def _replace_zero_signature(tx: Transaction, key_pair: Keypair):
    # get message
    message_content = tx.serialize_message()

    # sign message
    signed_message_content = key_pair.sign(message_content)

    # replace zero signature with signed message
    if not tx.signatures:
        raise Exception("transaction does not have any signatures")

    zero_sig_index = -1
    for index, pub_key_pair in enumerate(tx.signatures):
        if pub_key_pair.signature == None:
            if zero_sig_index != -1:
                raise Exception("more than one zero signature provided in transaction")
            zero_sig_index = index

    if zero_sig_index == -1:
        raise Exception("no zero signatures to replace in transaction")
    tx.signatures[zero_sig_index] = signed_message_content

if __name__ == "__main__":
    sign_tx("AAEAAQPT0EY4p9ErpYaI7SjuRYIJZnZGKpkE0ijKL5XDwhHK8Ntthose+d93bfMQ+Ry51ssLFMiRPqFe27iY7ryDPv3pAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwHDKRQmyQHHokjruWGNrJQWdcYM1ZcQimhLQNbLV0dgECAgABDAIAAAABAAAAAAAAAA==")