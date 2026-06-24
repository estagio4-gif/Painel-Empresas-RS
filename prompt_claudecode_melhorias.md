# Prompt — Melhorias no painel_rs.html

## Contexto

Tenho um dashboard HTML single-file em `painel_rs.html` (mesmo diretório).
É um painel tributário de empresas do RS que usa DuckDB-WASM no browser para consultar `explorer.parquet` (4,87M linhas, 32 colunas). O arquivo tem drawer lateral, filtros avançados, gráficos Chart.js e exportação CSV.

**Leia o `painel_rs.html` na íntegra antes de qualquer edição.**

---

## O que implementar — 6 melhorias em sequência

### A — Link CNPJ na Receita Federal + botão copiar (no drawer)

No cabeçalho do drawer (`drw-hd`), o CNPJ já aparece em `#drw-cnpj`.
- Transforme-o em link clicável que abre `https://solicitacao.servicos.gov.br/usuarios/login?qrCode=CNPJ_AQUI` em nova aba (ou use `https://www.receitafederal.gov.br/` se preferir a consulta pública direta).
- Adicione ao lado um botão pequeno "Copiar" que copia o CNPJ para a área de transferência com `navigator.clipboard.writeText()` e muda o texto para "Copiado ✓" por 1,5s.

### B — Campo de busca por CNPJ no explorador

No grupo de filtros "Cadastro & atividade", adicione um campo `<input id="fCnpj" placeholder="00.000.000/0000-00 ou só números">`.

No `buildWhere()`, acrescente:
```js
const cnpj = $('#fCnpj').value.replace(/\D/g,'');
if(cnpj) w.push(`replace(replace(replace(cnpj,'.',''),'/',''),'-','') LIKE '%${cnpj}%'`);
```

### C — Colunas da tabela clicáveis para ordenar

- Adicione estado de ordenação: `let sortCol = 'razao_social', sortDir = 'ASC'`.
- Ao renderizar o `<thead>`, envolva cada `<th>` com cursor pointer e um indicador visual (▲/▼/⇅).
- Ao clicar num cabeçalho: se `sortCol === col` inverte `sortDir`; senão muda `sortCol` e define `sortDir = 'ASC'`. Depois chama `runQuery(false)` (sem reset de página).
- Na query `runQuery`, substitua o `ORDER BY situacao, razao_social` fixo por `ORDER BY ${sortCol} ${sortDir}`.
- Colunas não ordenáveis: nenhuma — todas as 12 colunas devem ser ordenáveis.

### D — Chips de filtros ativos com × para remover

Logo abaixo dos botões "Aplicar / Limpar / Exportar" e acima do `#expStatus`, adicione uma `<div id="activeFilters">`.

Após cada execução de `runQuery(true)`, itere pelos filtros ativos e gere um chip para cada um no formato:
```html
<span class="chip">Regime: MEI <button>×</button></span>
```

O × de cada chip deve limpar só aquele filtro e re-executar `runQuery(true)`. Se não há filtros ativos, a div fica vazia (sem chips).

Mapeamento sugerido de ID → rótulo legível:
- `fNome` → "Nome"
- `fSecao` → "Setor"
- `fCnae` → "CNAE"
- `fNat` → "Natureza"
- `fMat` → "Matriz/Filial"
- `fSoc` → "Sócios"
- `fEmail` → "E-mail"
- `fTel` → "Telefone"
- `fRegime` → "Regime"
- `fSit` → "Situação"
- `fPorte` → "Porte"
- `fCap` → "Capital"
- `fAno` → "Abertura desde"
- `fMun` → "Município"
- `fDiv` → "Faixa dívida"
- `fCnpj` → "CNPJ"
- `m_pgfn` → "Dívida União"
- `m_comex` → "Comex"
- `m_anvisa` → "ANVISA"
- `m_pat` → "PAT"
- `m_energia` → "Energia"
- `m_ceis` → "CEIS"
- `m_cnep` → "CNEP"

Estilo do chip (adicionar no `<style>`):
```css
#activeFilters { display:flex; flex-wrap:wrap; gap:6px; margin:8px 2px 4px; }
.chip { display:inline-flex; align-items:center; gap:5px; background:#eef2f7; border:1px solid #d0d9e8; border-radius:14px; padding:3px 10px; font-size:12px; color:var(--navy); }
.chip button { background:none; border:none; cursor:pointer; color:var(--muted); font-size:13px; line-height:1; padding:0; }
.chip button:hover { color:var(--warn); }
```

### E — Link tel: e WhatsApp no telefone do drawer

Na função `openDrawer`, onde monta a seção Contato, substitua a linha do telefone:

```js
// antes
${row('Telefone', tel||null)}

// depois
const telNum = (r.telefone||'').replace(/\D/g,'');
const telHtml = telNum
  ? `${r.telefone} &nbsp;<a href="tel:${telNum}" style="font-size:11px;color:var(--navy)">[ligar]</a> &nbsp;<a href="https://wa.me/55${telNum}" target="_blank" style="font-size:11px;color:#25D366">[WhatsApp]</a>`
  : null;
${row('Telefone', telHtml)}
```

### G — Desabilitar faixa de dívida quando "Dívida União = Somente SEM"

No listener de `#m_pgfn` (já existe o listener de `.tri`), adicione lógica adicional:

```js
$('#m_pgfn').addEventListener('change', () => {
  const isSem = $('#m_pgfn').value === 'sem';
  $('#fDiv').disabled = isSem;
  if(isSem) $('#fDiv').value = '';
  $('#fDiv').closest('.fld').style.opacity = isSem ? '0.4' : '1';
});
```

---

## Regras gerais

- Não altere a paleta de cores nem o layout geral — apenas acrescente o que está descrito.
- Mantenha o arquivo como single-file (sem criar CSS ou JS separados).
- Teste mentalmente cada mudança: o drawer já usa `innerHTML`, então garanta que os links de `tel:` e `wa.me` não quebrem o escape de HTML.
- Após todas as edições, faça um diff do arquivo para confirmar que só as 6 melhorias foram tocadas.
