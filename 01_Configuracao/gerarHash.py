import bcrypt

usuarios = [
    # (nome,          login,  senha_em_texto, perfil)
    ("Pedro Arthur",    "Lazy",   "senha", "Dev"),
    ("Julia Lopes",     "jujuba", "senha", "Admin"),
    ("Gilberto Alves",  "giba",   "senha", "Supervisor"),
    ("eduarda isidorio","miora",  "senha", "Operador"),
]

print("-- Cole estes INSERTs no banco após rodar migracao_bcrypt.sql\n")

for nome, login, senha, perfil in usuarios:
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    print(
        f"INSERT INTO usuario (nome, login, senha, perfil) VALUES "
        f"('{nome}', '{login}', '{senha_hash}', '{perfil}');"
    )