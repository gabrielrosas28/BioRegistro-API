"""cria tabelas iniciais

Revision ID: 0001
Revises:
Create Date: 2026-11-22 15:24:35

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(nome: str, *valores: str) -> sa.Enum:
    return sa.Enum(*valores, name=nome, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("papel", _enum("papel", "coletor", "validador", "admin"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuarios")),
        sa.UniqueConstraint("email", name=op.f("uq_usuarios_email")),
    )

    op.create_table(
        "especies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_popular", sa.String(length=120), nullable=False),
        sa.Column("nome_cientifico", sa.String(length=160), nullable=False),
        sa.Column("familia", sa.String(length=120), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_especies")),
        sa.UniqueConstraint("nome_cientifico", name=op.f("uq_especies_nome_cientifico")),
    )

    op.create_table(
        "registros",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coletor_id", sa.Integer(), nullable=False),
        sa.Column("especie_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("uso_tradicional", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("foto_url", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            _enum("status_registro", "pendente", "validado", "rejeitado"),
            nullable=False,
        ),
        sa.Column("data_coleta", sa.Date(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name=op.f("ck_registros_latitude_valida")
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name=op.f("ck_registros_longitude_valida")
        ),
        sa.ForeignKeyConstraint(
            ["coletor_id"], ["usuarios.id"], name=op.f("fk_registros_coletor_id_usuarios")
        ),
        sa.ForeignKeyConstraint(
            ["especie_id"], ["especies.id"], name=op.f("fk_registros_especie_id_especies")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registros")),
    )
    op.create_index(op.f("ix_registros_coletor_id"), "registros", ["coletor_id"])
    op.create_index(op.f("ix_registros_especie_id"), "registros", ["especie_id"])
    op.create_index(op.f("ix_registros_status"), "registros", ["status"])
    op.create_index(op.f("ix_registros_atualizado_em"), "registros", ["atualizado_em"])
    op.create_index("ix_registros_lat_lon", "registros", ["latitude", "longitude"])

    op.create_table(
        "validacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registro_id", sa.Uuid(), nullable=False),
        sa.Column("validador_id", sa.Integer(), nullable=False),
        sa.Column("decisao", _enum("decisao", "aprovado", "rejeitado"), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["registros.id"], name=op.f("fk_validacoes_registro_id_registros")
        ),
        sa.ForeignKeyConstraint(
            ["validador_id"], ["usuarios.id"], name=op.f("fk_validacoes_validador_id_usuarios")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validacoes")),
    )
    op.create_index(op.f("ix_validacoes_registro_id"), "validacoes", ["registro_id"])
    op.create_index(op.f("ix_validacoes_validador_id"), "validacoes", ["validador_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_validacoes_validador_id"), table_name="validacoes")
    op.drop_index(op.f("ix_validacoes_registro_id"), table_name="validacoes")
    op.drop_table("validacoes")

    op.drop_index("ix_registros_lat_lon", table_name="registros")
    op.drop_index(op.f("ix_registros_atualizado_em"), table_name="registros")
    op.drop_index(op.f("ix_registros_status"), table_name="registros")
    op.drop_index(op.f("ix_registros_especie_id"), table_name="registros")
    op.drop_index(op.f("ix_registros_coletor_id"), table_name="registros")
    op.drop_table("registros")

    op.drop_table("especies")
    op.drop_table("usuarios")
