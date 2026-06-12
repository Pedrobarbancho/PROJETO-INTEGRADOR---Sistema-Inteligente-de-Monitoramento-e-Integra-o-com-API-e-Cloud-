import bcrypt

usuarios = [
    # (nome,          login,  senha_em_texto, perfil)
    ("Pedro Arthur Barbancho Santos",    "Lazy",   "senha", "Dev"),
    ("Julia Lopes da Silva",     "jujuba", "senha", "Admin"),
    ("Gilberto Alves Melo Ramos",  "giba",   "senha", "Supervisor"),
    ("Eduarda Isidorio da Silva","dudinha",  "senha", "Operador"),
]

print("-- Cole estes INSERTs no banco após rodar migracao_bcrypt.sql\n")

for nome, login, senha, perfil in usuarios:
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    print(
        f"INSERT INTO usuario (nome, login, senha, perfil) VALUES "
        f"('{nome}', '{login}', '{senha_hash}', '{perfil}');"
    )