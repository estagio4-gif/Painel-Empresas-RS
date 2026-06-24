# Lei do Bem — metodologia de estimativa de potencial

Objetivo: estimar **quantas empresas do RS poderiam usar a Lei do Bem (Lei 11.196/2005, arts. 17–26) e não usam**.

## 1. Requisitos legais (o que define elegibilidade)

A empresa precisa, cumulativamente:

1. **Estar no Lucro Real** (exclui MEI, Simples Nacional e Lucro Presumido). → filtro principal.
2. **Ter lucro fiscal no ano** (o benefício abate da base de IRPJ/CSLL; prejuízo fiscal zera o aproveitamento naquele ano).
3. **Ter regularidade fiscal** (CND/CPEND).
4. **Realizar PD&I** — pesquisa básica, aplicada ou desenvolvimento experimental (inovação tecnológica).

Não há aprovação prévia: a fruição é automática, mas a empresa **reporta anualmente ao MCTI** (FORMP&D), que publica os números e a lista de beneficiárias.

## 2. O funil aplicado ao painel

```
Total de estabelecimentos no RS
 → Ativas, NAO MEI, NAO Simples            (regime_tributario = 'Normal (Presumido/Real)')
 → Provavel Lucro Real                      (proxy: receita > R$ 78 mi/ano OU porte 'Demais' OU capital alto OU setor financeiro)
 → Em CNAE intensivo em P&D                 (cnae_pd_intensivo.csv: nivel Alta/Media)
 → Com regularidade fiscal                  (sem divida ativa bloqueante; debito SUSPENSO/GARANTIDO nao elimina)
 → MENOS as beneficiarias do MCTI           (flag_lei_do_bem)
 = POTENCIAIS NAO-USUARIAS                   <- o numero-alvo
 (priorizar as com sinais de inovacao: flag_inova = INPI/FINEP/EMBRAPII)
```

O painel implementa hoje as 3 primeiras linhas (filtros "Intensidade de P&D" e "Potencial Lei do Bem"). As duas últimas (subtrair beneficiárias e priorizar por inovação) entram quando o `explorer.parquet` for enriquecido pelo script `montar_flags_leidobem.py`.

## 3. Score de aderência (0–100)

Calculado por `montar_flags_leidobem.py` apenas para quem **ainda não é** beneficiária:

| Critério | Pontos |
|---|---|
| Regime Normal (não Simples/MEI) | +40 |
| CNAE de P&D **Alta** / **Média** | +25 / +15 |
| Sinal de inovação (INPI/FINEP) — `flag_inova` | +20 |
| Porte 'Demais' OU capital ≥ R$ 1 mi (proxy de tamanho) | +15 |
| Dívida ativa União (atenção à regularidade) | −10 |

(Limitado a um mínimo de 0. Quem já é beneficiária recebe `score = NULL` e `flag_lei_do_bem = true`.)

## 4. Fontes de dados a baixar (para os flags)

| Flag | Fonte oficial | Onde baixar | Como casa com o painel |
|---|---|---|---|
| `flag_lei_do_bem` | MCTI — Relatório Anual da Utilização dos Incentivos Fiscais (lista de empresas beneficiárias) | gov.br/mcti → "Lei do Bem" → relatórios anuais | por CNPJ (14 díg.); fallback por raiz (8 díg.) p/ grupo |
| `flag_inova` (patente/software) | INPI — dados abertos (patentes, programas de computador, marcas) | gov.br/inpi → estatísticas/dados abertos | por CNPJ do depositante; fallback por razão social normalizada |
| `flag_inova` (fomento) | FINEP / BNDES — transparência | finep.gov.br / bndes.gov.br | por CNPJ |
| (opcional) EMBRAPII | lista de empresas parceiras | embrapii.org.br | por CNPJ/nome |
| Faturamento (proxy Lucro Real) | Econodata / Serasa (privado) ou RAIS (nº empregados) | — | por CNPJ |

## 5. Ressalvas (exibir no painel)

- A elegibilidade é **anual e autodeclaratória**: o painel estima *potencial*, não confirma direito ao benefício.
- **Prejuízo fiscal** zera o aproveitamento no ano — sem demonstrações financeiras, fica como incerteza.
- `flag_pgfn` (dívida União) **não** elimina sozinho: débito **suspenso ou garantido** preserva a regularidade. Trate como "atenção".
- A separação Lucro Real × Presumido é **proxy** (a Receita não publica). O sinal mais forte é receita > R$ 78 mi/ano (Lucro Real obrigatório, Lei 9.718/98).
- A lista de CNAEs (`cnae_pd_intensivo.csv`) segue a intensidade tecnológica da OCDE/Eurostat ajustada à realidade brasileira da Lei do Bem; revise conforme o foco do estudo.

## 6. Como rodar o enriquecimento

```bash
python montar_flags_leidobem.py \
  --explorer explorer.parquet \
  --cnae cnae_pd_intensivo.csv \
  --mcti mcti_beneficiarias.csv \
  --inpi inpi_depositantes.csv \
  --out explorer_enriquecido.parquet
```

`--mcti` e `--inpi` são opcionais; sem eles os flags ficam `false` e só `pd_nivel` + `score` (parcial) são preenchidos. Depois, renomeie `explorer_enriquecido.parquet` para `explorer.parquet` (faça backup) para o painel passar a enxergar as novas colunas.
