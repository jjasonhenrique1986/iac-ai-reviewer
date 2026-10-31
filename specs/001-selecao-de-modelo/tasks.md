# Tasks: Seleção do modelo de IA

**Input**: Design documents from `/specs/001-selecao-de-modelo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: obrigatórios (Constituição, Princípio V), sem acesso à AWS.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: história da spec (US1, US2, US3)

## Phase 1: Setup

- [x] T001 Fixar `boto3==1.43.123` em `reviewer/requirements.txt`

## Phase 2: Foundational

- [x] T002 Criar `SupportedModel` e `SUPPORTED_MODELS` (4 modelos, data-model.md) em `reviewer/review.py`
- [x] T003 Criar `resolve_model(model_id)` que aplica o padrão para vazio e rejeita IDs fora da lista em
  `reviewer/review.py`

**Checkpoint**: lista e validação prontas; o fluxo atual do Claude continua igual.

## Phase 3: User Story 1 - Escolher o modelo da revisão (P1) 🎯 MVP

**Goal**: `MODEL_ID` escolhe entre Claude (Mantle) e gpt-oss (Converse).

**Independent Test**: `pytest` com Stubber do Converse gera uma revisão válida para `openai.gpt-oss-120b-1:0`.

- [x] T004 [P] [US1] Testes: `resolve_model` (vazio, válido, inválido) em `tests/test_review.py`
- [x] T005 [P] [US1] Testes: Converse com ferramenta forçada, schema expandido, nova tentativa e falha após
  duas respostas inválidas, usando `botocore.stub.Stubber`, em `tests/test_review.py`
- [x] T006 [US1] Implementar `review_schema()` (schema expandido, sem `$ref`) em `reviewer/review.py`
- [x] T007 [US1] Implementar `ask_converse(client, model_id, prompt)` com ferramenta forçada, validação e
  uma nova tentativa em `reviewer/review.py`
- [x] T008 [US1] Em `main()`, escolher Mantle ou Converse pelo `api` do modelo; modelo não suportado vira
  mensagem com a lista de aceitos, sem chamar o Bedrock, em `reviewer/review.py`
- [x] T009 [US1] Validar `FALLBACK_MODEL_ID` (só `mantle`, deve estar na lista) em `reviewer/review.py`

**Checkpoint**: US1 funcional e testada.

## Phase 4: User Story 2 - Ver quais modelos estão disponíveis (P2)

**Goal**: `--list-models [--test]` mostra a lista com o status do acordo e, opcionalmente, uma chamada mínima.

**Independent Test**: `pytest` com Stubber do cliente `bedrock` gera a tabela, inclusive o caso sem permissão.

- [x] T010 [P] [US2] Testes: tabela com acordo `AVAILABLE`/`NOT_AVAILABLE` e coluna `desconhecido` quando
  não há permissão, em `tests/test_review.py`
- [x] T011 [US2] Implementar `list_models(test: bool)` e as opções `--list-models` e `--test` (sem exigir
  `--base`) em `reviewer/review.py`

**Checkpoint**: US1 e US2 funcionam de forma independente.

## Phase 5: User Story 3 - Entender por que o modelo falhou (P3)

**Goal**: erros de acesso, cota, modelo inexistente e limite viram mensagens claras (research.md, item 4).

**Independent Test**: `pytest` simula 403/404 no Mantle e `AccessDeniedException`/`ResourceNotFoundException`/
`ThrottlingException` no Converse e confere as mensagens.

- [x] T012 [P] [US3] Testes: mapeamento de erros do Mantle (servidor local respondendo 403/404) e do
  Converse (Stubber) em `tests/test_review.py`
- [x] T013 [US3] Implementar `explain_error(exc)` e usar nos dois caminhos em `reviewer/review.py`

## Phase 6: Polish & Cross-Cutting

- [x] T014 [P] README: lista de modelos, como escolher (`MODEL_ID`), `--list-models`, IAM por modelo em
  `README.md`
- [x] T015 [P] IAM: `bedrock:InvokeModel` nos ARNs gpt-oss na política da role do GitHub em
  `aws-iam-baseline/main.tf` (outro repositório; `apply` feito pelo usuário)
- [x] T016 [P] IAM: permission set `IacAiReviewer` e perfil `iac-ai-reviewer` no `~/.aws/config` (CLI)
- [x] T017 Rodar `pytest` e os cenários 2 a 4 do quickstart.md com o perfil `iac-ai-reviewer`
- [x] T018 Cenário 5 do quickstart.md (GitHub) depois do `apply` de T015

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T003) → US1 → US2 e US3 (independentes entre si) → Polish.
- T015 e T016 não dependem do código e podem ser feitos a qualquer momento; T017 depende de T016, T018 de T015.

## Parallel Example: User Story 1

```text
T004 e T005 (testes) em paralelo; depois T006 → T007 → T008 → T009.
```

## Implementation Strategy

MVP = Setup + Foundational + US1: o revisor já funciona com gpt-oss. US2 e US3 melhoram a experiência e
podem entrar no mesmo PR.
