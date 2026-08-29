---
name: refactor-arch
description: Audita e refatora uma codebase inteira para o padrão MVC em três fases sequenciais — análise da stack, auditoria de anti-patterns com relatório classificado por severidade, e refatoração validada. Agnóstica de linguagem e framework (Python/Flask, Node/Express, PHP, Java, Go, Ruby...). Use quando o usuário pedir /refactor-arch, auditoria de arquitetura, detecção de code smells, relatório de severidades, ou refatoração de projeto legado para MVC.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---

# refactor-arch — Auditoria e Refatoração Arquitetural

Transforma qualquer projeto legado em uma aplicação MVC limpa, em **três fases sequenciais**
com um portão humano entre a auditoria e a escrita de código.

```
FASE 1 — ANÁLISE      →  FASE 2 — AUDITORIA      →  [confirmação humana]  →  FASE 3 — REFATORAÇÃO
detecta stack,           cruza o código contra                                reestrutura em MVC,
arquitetura e            o catálogo, emite o                                  valida boot + endpoints
superfície HTTP          relatório de severidades
```

## Regras invioláveis

1. **Nenhum arquivo é criado, movido ou modificado antes da resposta `y` na Fase 2.** As Fases 1 e 2
   são estritamente somente-leitura. Isso inclui não criar diretórios, não rodar formatadores e
   não escrever o relatório dentro do projeto antes da confirmação.
2. **Todo achado precisa de `arquivo:linha` verificado.** Leia com `cat -n` (ou equivalente) e
   confira o número antes de escrever. Nunca estime linha.
3. **Paridade de contrato HTTP.** Depois da refatoração, todo endpoint original responde no mesmo
   método, mesma rota e mesmo status para as mesmas entradas. Rota removida ou renomeada = falha.
   A única exceção permitida é o fechamento de um endpoint *inseguro por natureza*, que precisa ser
   listado explicitamente no resumo da Fase 3 e justificado (ver `references/mvc-architecture.md`).
4. **Nada de stack inventada.** Framework, versão e banco vêm sempre de um arquivo de manifesto real
   (`requirements.txt`, `package.json`, `go.mod`, `pom.xml`, `composer.json`, `Gemfile`...) ou de um
   import no código. Se não houver evidência, escreva `desconhecido`.
5. **Segredos saem do código, mas não entram no repositório.** Credenciais hardcoded viram variáveis
   de ambiente com *default de desenvolvimento* e um `.env.example` versionado. Nunca versione `.env`.
6. **A aplicação precisa continuar rodando.** Uma Fase 3 que não passa na validação não está concluída:
   corrija até passar ou reverta.

## Fase 1 — Análise do projeto

Objetivo: entender o que é este projeto antes de julgá-lo.

Leia `references/project-analysis.md` e siga o procedimento de detecção. Em resumo:

1. Detecte **linguagem** e **framework + versão** pelo manifesto de dependências e pelos imports.
2. Mapeie os **arquivos de código-fonte** (exclua `node_modules/`, `.venv/`, `venv/`, `.git/`,
   `dist/`, `build/`, `__pycache__/`, lockfiles e binários) e conte linhas.
3. Identifique o **domínio de negócio** pelos nomes de tabelas, rotas e entidades — descreva em
   uma frase, em português.
4. Descreva a **arquitetura atual** em uma frase (monolítica em N arquivos / camadas parciais /
   MVC incompleto...).
5. Extraia o **banco e as tabelas** (DDL, models ORM ou migrations).
6. Extraia o **inventário completo de endpoints** (`MÉTODO /rota`). Salve essa lista: ela é o
   contrato que a Fase 3 tem de preservar.

Imprima exatamente neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão quando detectável>
Framework:     <framework + versão>
Dependencies:  <libs relevantes, separadas por vírgula>
Domain:        <domínio em uma frase>
Architecture:  <arquitetura atual em uma frase>
Source files:  <N> files analyzed (<M> lines)
DB tables:     <tabelas separadas por vírgula>
Endpoints:     <N> endpoints mapeados
================================
```

## Fase 2 — Auditoria

Objetivo: transformar o código em uma lista priorizada de problemas reais, com evidência.

1. Leia `references/antipatterns-catalog.md`. Ele é a **fonte da verdade** de nomes canônicos,
   sinais de detecção e severidade — não invente classificações próprias.
2. Percorra **cada arquivo de código-fonte** e cruze contra o catálogo. Rode as buscas objetivas
   sugeridas em cada entrada (`grep`, leitura dirigida). Cubra as sete famílias:
   segurança, arquitetura/MVC, SOLID/acoplamento, dados/performance, APIs deprecated,
   duplicação/padronização e legibilidade.
3. **Verifique cada achado antes de escrevê-lo**: abra o arquivo na linha citada e confirme que o
   trecho está lá. Achado sem evidência literal é descartado.
4. Deduplique: mesmo problema no mesmo arquivo vira **um** achado com intervalo de linhas.
   O mesmo padrão em arquivos diferentes vira achados separados.
5. Classifique pela escala de severidade (`references/antipatterns-catalog.md` §Severidades) e
   **ordene CRITICAL → HIGH → MEDIUM → LOW**.
6. Emita o relatório no formato de `references/audit-report-template.md`.
7. Se o usuário pediu o relatório em arquivo, **anuncie o caminho mas só escreva depois do `y`**
   (regra inviolável 1). O destino convencional é `reports/audit-<projeto>.md`.

Encerre a fase com a pergunta de confirmação, exatamente assim:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Use `AskUserQuestion` quando a ferramenta estiver disponível; caso contrário, faça a pergunta em
texto e **pare o turno ali**, aguardando a resposta. Respostas diferentes de `y`/`yes`/`sim`
encerram a execução sem tocar em nenhum arquivo — nesse caso, ofereça salvar apenas o relatório.

## Fase 3 — Refatoração

Só começa após a confirmação explícita.

1. Leia `references/mvc-architecture.md` (estrutura-alvo e regras de camada) e
   `references/refactoring-playbook.md` (transformação concreta para cada anti-pattern).
2. **Fixe o baseline antes de mexer**: suba a aplicação original e grave a resposta de cada
   endpoint do inventário da Fase 1 (`references/validation.md` traz o harness pronto).
   Se a aplicação não sobe nem antes da refatoração, registre isso no relatório e siga com
   validação estática (import/boot) em vez de comparação de respostas.
3. Reestruture seguindo a ordem de menor risco:
   `config` → `models` → `controllers` (regra de negócio) → `views/routes` → `middlewares` →
   composition root. Aplique um padrão do playbook por vez.
4. Elimine os achados da Fase 2 — cada CRITICAL e HIGH precisa ter tratamento. Um achado que você
   decidir não corrigir tem de aparecer como *aceito conscientemente* no resumo, com justificativa.
5. Remova os arquivos legados que foram substituídos (não deixe o código antigo órfão ao lado do
   novo) e atualize `README.md`/scripts de execução do projeto para o novo entry point.
6. **Valide** conforme `references/validation.md`:
   - a aplicação sobe sem erro;
   - todos os endpoints do inventário respondem com o mesmo status do baseline;
   - uma nova varredura do catálogo não encontra mais nenhum CRITICAL/HIGH introduzido;
   - se o projeto tem testes, eles continuam passando.
7. Imprima o resumo final:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
<árvore de diretórios resultante>

Findings resolved: <N>/<total>  (CRITICAL <n>/<n> | HIGH <n>/<n> | MEDIUM <n>/<n> | LOW <n>/<n>)

Validation
  ✓ Application boots without errors
  ✓ <N>/<N> endpoints respond with baseline parity
  ✓ Zero CRITICAL/HIGH anti-patterns remaining
================================
```

Marque com `✗` o que falhar — nunca reporte sucesso não verificado.

## Referências

| Arquivo | Quando ler |
|---|---|
| `references/project-analysis.md` | Fase 1 — heurísticas de detecção de linguagem, framework, banco, domínio e endpoints |
| `references/antipatterns-catalog.md` | Fase 2 — catálogo de anti-patterns, sinais de detecção e escala de severidade |
| `references/audit-report-template.md` | Fase 2 — formato exato do relatório de auditoria |
| `references/mvc-architecture.md` | Fase 3 — estrutura-alvo MVC e regras de cada camada |
| `references/refactoring-playbook.md` | Fase 3 — transformações concretas antes/depois por anti-pattern |
| `references/validation.md` | Fase 3 — protocolo de validação de boot e paridade de endpoints |

## Escopo

Esta skill assume um projeto de aplicação (API, web app ou serviço) com uma superfície de entrada
identificável. Para bibliotecas sem entry point HTTP, execute as Fases 1 e 2 normalmente e, na
Fase 3, troque a validação por "importa sem erro + suíte de testes passa".
