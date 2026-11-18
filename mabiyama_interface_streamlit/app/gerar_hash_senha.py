"""Gera o hash SHA-256 de uma senha para colar em .streamlit/secrets.toml (a senha em si nunca fica no projeto)."""
import getpass, hashlib
s = getpass.getpass("Senha: ")
print(hashlib.sha256(s.encode("utf-8")).hexdigest())
