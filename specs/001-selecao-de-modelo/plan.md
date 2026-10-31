# Implementation Plan: Seleção do modelo de IA

**Branch**: `sdd-selecao-de-modelo` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-selecao-de-modelo/spec.md`

## Summary

Permitir escolher o modelo da revisão por `MODEL_ID`, numa lista fechada de modelos suportados (Claude Opus
5.5 e 4.8, OpenAI gpt-oss-120b e 20b), e listar esses modelos com o status na conta (`--list-models`).
Os modelos Claude continuam no `AnthropicBedrockMantle`; os gpt-oss usam a API Converse do Bedrock com
ferramenta forçada e schema expandido, validados pelo mesmo Pydantic `Review`
(ver [research.md](research.md)). Erros de acesso, cota e formato viram mensagens claras no comentário.

## Technical Context

**Language/Version**: Python 3.12 (workflow); testado também em 3.11

**Primary Dependencies**: `anthropic[bedrock]==2.3.0`, `pydantic==2.14.2`, `boto3==1.43.123` (fixado agora
porque passa a ser usado diretamente)

**Storage**: N/A

**Testing**: pytest, com servidor HTTP local para o Mantle (já existe) e `botocore.stub.Stubber` para o Converse

**Target Platform**: GitHub Actions (`ubuntu-latest`) e máquina local com SSO

**Project Type**: CLI de arquivo único (`reviewer/review.py`)

**Performance Goals**: `--list-models` em menos de 30 s para 4 modelos (SC-003)

**Constraints**: sem credenciais fixas; sem rede da AWS nos testes; IAM por modelo

**Scale/Scope**: 4 modelos suportados; um PR por execução

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Status |
|---|---|---|
| I. Sem credenciais fixas | Converse e Mantle usam a cadeia padrão de credenciais (OIDC/SSO) | ✅ |
| II. Menor privilégio | Lista fechada; IAM libera só os 2 ARNs gpt-oss; permission set `IacAiReviewer` com o nome do projeto | ✅ |
| III. A IA explica, não decide | Toda falha vira mensagem; código de saída 0 quando há comentário | ✅ |
| IV. Saída validada | Mesmo `Review` para todos; nova tentativa e falha explícita no Converse | ✅ |
| V. Testável sem AWS | Stubber do botocore para o Converse; servidor local para o Mantle | ✅ |
| VI. Português | Mensagens, README e specs em pt-BR; exemplos fictícios | ✅ |

Reavaliado após o desenho (Phase 1): sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/001-selecao-de-modelo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
reviewer/
├── review.py            # SUPPORTED_MODELS, escolha, Converse, --list-models, mensagens de erro
└── requirements.txt     # + boto3 fixado
tests/
└── test_review.py       # novos cenários com Stubber e servidor local
README.md                # lista de modelos, como escolher, --list-models, IAM por modelo
```

Fora deste repositório (Constituição, Fluxo de desenvolvimento):

```text
aws-iam-baseline/main.tf           # bedrock:InvokeModel nos ARNs gpt-oss na política da role do GitHub
IAM Identity Center (manual, CLI)  # permission set IacAiReviewer + perfil iac-ai-reviewer no ~/.aws/config
```

**Structure Decision**: manter o arquivo único `reviewer/review.py`. A mudança acrescenta umas 100 linhas,
e separar em módulos agora complicaria o workflow (`python reviewer/review.py`) sem ganho.

## Complexity Tracking

Sem violações a justificar.
