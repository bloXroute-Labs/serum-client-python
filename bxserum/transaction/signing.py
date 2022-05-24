import os
import base58
import base64
from solana.keypair import Keypair
from solana.transaction import Transaction


def load_private_key() -> Keypair:
    # get base58 encoded private key
    pkey_str = os.getenv("PRIVATE_KEY")
    if pkey_str is None:
        raise EnvironmentError("env variable `PRIVATE_KEY` not set")

    # convert base58 private key string to a keypair
    pkey_bytes = bytes(pkey_str, encoding="utf-8")
    pkey_bytes_base58 = base58.b58decode(pkey_bytes)
    return Keypair.from_secret_key(pkey_bytes_base58)


def sign_tx(unsigned_tx_base64: str) -> str:
    """
    Uses environment variable `PRIVATE_KEY` to sign message content and replace zero signatures.

    :param unsigned_tx_base64: transaction bytes in base64
    :return: signed transaction
    """
    keypair = load_private_key()
    return sign_tx_with_private_key(unsigned_tx_base64, keypair)


def sign_tx_with_private_key(unsigned_tx_base64: str, keypair: Keypair) -> str:
    """
    Signs message content and replaces placeholder zero signature with signature.

    :param unsigned_tx_base64: transaction bytes in base64
    :param keypair: key pair to sign with
    :return: signed transaction
    """
    # convert base64 transaction string to a transaction
    tx_bytes = bytes(unsigned_tx_base64, encoding="utf-8")
    tx_bytes_base64 = base64.decodebytes(tx_bytes)
    tx = Transaction.deserialize(tx_bytes_base64)

    # sign transaction using keypair
    _sign_tx(tx, keypair)

    # convert transaction back to base64
    signed_tx_bytes_base64 = base64.b64encode(tx.serialize())
    return signed_tx_bytes_base64.decode("utf-8")


def _sign_tx(tx: Transaction, keypair: Keypair):
    signatures_required = tx.compile_message().header.num_required_signatures
    signatures_present = len(tx.signatures)
    if signatures_present != signatures_required:
        raise Exception(
            f"transaction requires {signatures_required} signatures and has {signatures_present} signatures"
        )

    _replace_zero_signature(tx, keypair)


def _replace_zero_signature(tx: Transaction, keypair: Keypair):
    message_content = tx.serialize_message()
    signed_message_content = keypair.sign(message_content)
    new_signature = signed_message_content.signature

    if not tx.signatures:
        raise Exception("transaction does not have any signatures")

    zero_sig_index = -1
    for index, pub_keypair in enumerate(tx.signatures):
        if pub_keypair.signature == None:
            if zero_sig_index != -1:
                raise Exception("more than one zero signature provided in transaction")
            zero_sig_index = index

    if zero_sig_index == -1:
        raise Exception("no zero signatures to replace in transaction")
    tx.signatures[zero_sig_index].signature = new_signature
