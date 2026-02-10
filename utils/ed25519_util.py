from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class ED25519Util:
    @staticmethod
    def generate() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        """
        生成 ed25519 密钥对

        Returns:
            tuple[Ed25519PrivateKey, Ed25519PublicKey]: 密钥对(私钥, 公钥)

        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def load(
        private_key_path: Path,
        public_key_path: Path,
    ):
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                data=f.read(),
                password=None,
            )
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(data=f.read())

        if not isinstance(private_key, Ed25519PrivateKey):
            raise Exception(
                f"{private_key_path} is not a ed25519 private key, "
                f"{type(private_key)}"
            )
        if not isinstance(public_key, Ed25519PublicKey):
            raise Exception(
                f"{public_key_path} is not a ed25519 private key, "
                f"{type(public_key)}"
            )
        return private_key, public_key

    @staticmethod
    def serialize(key: Ed25519PrivateKey | Ed25519PublicKey) -> str:
        """返回字符串类型的 key"""
        if isinstance(key, Ed25519PrivateKey):
            return key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()
        return key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    @staticmethod
    def sign(private_key: Ed25519PrivateKey, data: bytes) -> bytes:
        """
        使用私钥给 data 签名

        Args:
            private_key (Ed25519PrivateKey): ed25519 私钥
            data (bytes): 待签名数据

        Returns:
            bytes: 签名

        """
        return private_key.sign(data=data)

    @staticmethod
    def verify(
        data: bytes,
        signature: bytes,
        public_key: Ed25519PublicKey,
    ) -> bool:
        """
        验证 data 对应的 ed25519 签名是否正确

        Args:
            data (bytes): 被签名数据
            signature (bytes): 签名
            public_key (Ed25519PublicKey): 公钥

        Returns:
            bool: True 签名正确; False 签名错误
        """
        try:
            public_key.verify(signature=signature, data=data)
            return True
        except InvalidSignature:
            return False


if __name__ == "__main__":
    pri, pub = ED25519Util.generate()
    print("private:", ED25519Util.serialize(pri))
    print("public:", ED25519Util.serialize(pub))
