# -*- coding: utf-8 -*-
"""
Enriquece o explorer.parquet com indicadores de potencial da Lei do Bem.

Colunas adicionadas:
  pd_nivel           -> 'Alta' | 'Media' | NULL  (intensidade de P&D do CNAE principal)
  flag_lei_do_bem    -> BOOLEAN  (consta na lista de beneficiarias do MCTI)
  flag_inova         -> BOOLEAN  (consta no INPI / FINEP / etc.)
  score_lei_do_bem   -> INTEGER 0..100 (so para quem NAO e beneficiaria; senao NULL)

Uso:
  python montar_flags_leidobem.py \
      --explorer explorer.parquet \
      --cnae cnae_pd_intensivo.csv \
      [--mcti mcti_beneficiarias.csv] \
      [--inpi inpi_depositantes.csv] \
      --out explorer_enriquecido.parquet

--mcti e --inpi sao OPCIONAIS. Sem eles os flags ficam False.
Os CSVs de MCTI/INPI so precisam ter uma coluna com 'cnpj' no nome
(o script normaliza para 14 digitos). O INPI tambem aceita casar por
razao social: use --inpi-coluna-nome NOME_DA_COLUNA.

Requisitos: pip install duckdb pandas
"""
import argparse
import re
import sys
import unicodedata
import duckdb
import pandas as pd


def only_digits(s):
    return re.sub(r"\D", "", str(s if s is not None else ""))


def strip_accents(s):
    s = str(s if s is not None else "")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def find_cnpj_column(df):
    for c in df.columns:
        if "cnpj" in strip_accents(c).lower():
            return c
    return None


def load_cnae_levels(path):
    """Le a lista curada e devolve (alta_div, alta_classe, media_div) como listas de strings."""
    df = pd.read_csv(path, sep=";", dtype=str).fillna("")
    df["nivel_n"] = df["nivel"].map(lambda x: strip_accents(x).strip().lower())
    df["tipo_n"] = df["tipo"].map(lambda x: strip_accents(x).strip().lower())
    df["cod"] = df["codigo"].map(lambda x: x.strip())
    alta_div = sorted({r.cod for r in df.itertuples() if r.nivel_n == "alta" and r.tipo_n == "divisao"})
    alta_cl = sorted({r.cod for r in df.itertuples() if r.nivel_n == "alta" and r.tipo_n == "classe"})
    media_div = sorted({r.cod for r in df.itertuples() if r.nivel_n == "media" and r.tipo_n == "divisao"})
    return alta_div, alta_cl, media_div


def sql_list(values):
    return ",".join("'" + v.replace("'", "''") + "'" for v in values) or "''"


def load_cnpj_set(path, label):
    """Carrega um CSV qualquer e devolve um DataFrame com uma unica coluna 'cnpj' (14 digitos)."""
    if not path:
        return pd.DataFrame({"cnpj": pd.Series(dtype=str)})
    sep = ";" if ";" in open(path, "r", encoding="utf-8", errors="ignore").readline() else ","
    df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8", on_bad_lines="skip").fillna("")
    col = find_cnpj_column(df)
    if not col:
        print(f"[AVISO] {label}: nenhuma coluna com 'cnpj' encontrada em {path}. Flag ficara False.")
        return pd.DataFrame({"cnpj": pd.Series(dtype=str)})
    out = pd.DataFrame({"cnpj": df[col].map(only_digits)})
    out = out[out["cnpj"].str.len() == 14].drop_duplicates()
    print(f"[OK] {label}: {len(out):,} CNPJs validos carregados de '{col}'.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explorer", default="explorer.parquet")
    ap.add_argument("--cnae", default="cnae_pd_intensivo.csv")
    ap.add_argument("--mcti", default=None, help="CSV das beneficiarias da Lei do Bem (MCTI)")
    ap.add_argument("--inpi", default=None, help="CSV de depositantes INPI/FINEP")
    ap.add_argument("--out", default="explorer_enriquecido.parquet")
    args = ap.parse_args()

    alta_div, alta_cl, media_div = load_cnae_levels(args.cnae)
    print(f"[OK] CNAE: {len(alta_div)} divisoes Alta, {len(alta_cl)} classes Alta, {len(media_div)} divisoes Media.")

    mcti = load_cnpj_set(args.mcti, "MCTI")
    inpi = load_cnpj_set(args.inpi, "INPI")

    con = duckdb.connect()
    con.register("mcti", mcti)
    con.register("inpi", inpi)

    cnpj_norm = "regexp_replace(e.cnpj,'[^0-9]','','g')"
    alta_expr = (
        f"(substr(e.cnae_principal,1,4) IN ({sql_list(alta_cl)}) "
        f"OR substr(e.cnae_principal,1,2) IN ({sql_list(alta_div)}))"
    )
    media_expr = f"(substr(e.cnae_principal,1,2) IN ({sql_list(media_div)}))"

    pd_nivel = f"CASE WHEN {alta_expr} THEN 'Alta' WHEN {media_expr} THEN 'Media' ELSE NULL END"
    is_benef = "(m.cnpj IS NOT NULL)"
    is_inova = "(i.cnpj IS NOT NULL)"

    score = f"""
      CASE WHEN {is_benef} THEN NULL ELSE greatest(0,
          (CASE WHEN e.regime_tributario = 'Normal (Presumido/Real)' THEN 40 ELSE 0 END)
        + (CASE WHEN {alta_expr} THEN 25 WHEN {media_expr} THEN 15 ELSE 0 END)
        + (CASE WHEN {is_inova} THEN 20 ELSE 0 END)
        + (CASE WHEN e.porte = 'Demais' OR e.capital_social >= 1000000 THEN 15 ELSE 0 END)
        - (CASE WHEN e.flag_pgfn THEN 10 ELSE 0 END)
      ) END
    """

    sql = f"""
    COPY (
      SELECT e.*,
             {pd_nivel}                AS pd_nivel,
             {is_benef}                AS flag_lei_do_bem,
             {is_inova}                AS flag_inova,
             {score}                   AS score_lei_do_bem
      FROM read_parquet('{args.explorer}') e
      LEFT JOIN mcti m ON {cnpj_norm} = m.cnpj
      LEFT JOIN inpi i ON {cnpj_norm} = i.cnpj
    ) TO '{args.out}' (FORMAT PARQUET);
    """
    print("[..] Gerando parquet enriquecido (pode levar 1-2 min)...")
    con.execute(sql)

    # Resumo
    r = con.execute(f"""
      SELECT
        count(*) total,
        count(*) FILTER (WHERE pd_nivel IS NOT NULL) com_pd,
        count(*) FILTER (WHERE flag_lei_do_bem) ja_usam,
        count(*) FILTER (WHERE situacao='Ativa'
                          AND regime_tributario='Normal (Presumido/Real)'
                          AND pd_nivel IS NOT NULL
                          AND NOT flag_lei_do_bem) potenciais
      FROM read_parquet('{args.out}')
    """).fetchone()
    print("\n===== RESUMO =====")
    print(f"Total de estabelecimentos ....... {r[0]:,}")
    print(f"Em CNAE intensivo em P&D ........ {r[1]:,}")
    print(f"Ja usam a Lei do Bem (MCTI) ..... {r[2]:,}")
    print(f"POTENCIAIS nao-usuarias ......... {r[3]:,}")
    print(f"\nArquivo gerado: {args.out}")
    print("Para o painel enxergar: faca backup do explorer.parquet e renomeie o novo no lugar.")


if __name__ == "__main__":
    main()
