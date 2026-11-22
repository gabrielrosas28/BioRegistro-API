import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Papel
from app.schemas.usuario import UsuarioCriacao
from app.services.erros import Conflito
from app.services.usuario import UsuarioService


def main(
    argv: Sequence[str] | None = None,
    fabrica_sessao: Callable[[], Session] = SessionLocal,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.criar_admin",
        description="Cria um usuário administrador.",
    )
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", help="se omitida, é pedida no terminal")
    args = parser.parse_args(argv)

    senha = args.senha if args.senha is not None else getpass.getpass("Senha: ")
    try:
        dados = UsuarioCriacao(nome=args.nome, email=args.email, senha=senha, papel=Papel.ADMIN)
    except ValidationError as erro:
        for item in erro.errors():
            campo = ".".join(str(parte) for parte in item["loc"])
            print(f"{campo}: {item['msg']}", file=sys.stderr)
        return 1

    with fabrica_sessao() as db:
        try:
            usuario = UsuarioService(db).cadastrar(dados)
        except Conflito as erro:
            print(erro.mensagem, file=sys.stderr)
            return 1

    print(f"Administrador criado: {usuario.email} (id {usuario.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
