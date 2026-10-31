# Quickstart: validar a seleção do modelo

## Pré-requisitos

- Python 3.12 e `pip install -r requirements-dev.txt`.
- Para os cenários com AWS: login SSO e o perfil `iac-ai-reviewer`
  (`aws sso login --sso-session <sessão>`), com o permission set `IacAiReviewer`.

## 1. Testes automatizados (sem AWS)

```bash
pytest
```

Esperado: todos passam, incluindo os cenários de escolha de modelo, modelo não suportado, Converse com
ferramenta, nova tentativa em resposta inválida e mapeamento de erros.

## 2. Lista de modelos

```bash
AWS_PROFILE=iac-ai-reviewer python reviewer/review.py --list-models --test
```

Esperado: os 4 modelos suportados com o status do acordo e o resultado da chamada mínima
(ver [contracts/cli.md](contracts/cli.md)).

## 3. Revisão com um modelo gpt-oss

Num checkout com mudanças em `examples/`:

```bash
AWS_PROFILE=iac-ai-reviewer MODEL_ID=openai.gpt-oss-120b-1:0 \
  python reviewer/review.py --base <ref-base> --output review.md
```

Esperado: `review.md` com a revisão e o rodapé citando `openai.gpt-oss-120b-1:0`.

## 4. Modelo não suportado

```bash
MODEL_ID=modelo.qualquer python reviewer/review.py --base <ref-base>
```

Esperado: nenhuma chamada ao Bedrock; o comentário diz que o modelo não é suportado e lista os aceitos.

## 5. No GitHub

Definir a variável `MODEL_ID=openai.gpt-oss-120b-1:0` no repositório e abrir um PR com mudança em `.tf`.
Esperado: comentário gerado pelo gpt-oss. Requer a política da role `gh-iac-ai-reviewer` atualizada.
