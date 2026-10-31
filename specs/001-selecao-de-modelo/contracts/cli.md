# Contrato: linha de comando e configuração

## Revisão (comportamento atual, estendido)

```text
python reviewer/review.py --base <ref> [--checkov <arquivo>] [--output review.md]
```

| Variável | Padrão | Regra |
|---|---|---|
| `MODEL_ID` | `anthropic.claude-opus-5-5` | deve estar em `SUPPORTED_MODELS` |
| `FALLBACK_MODEL_ID` | `anthropic.claude-opus-4-8` | só para modelos `mantle`; deve estar na lista |
| `AWS_REGION` | `us-east-1` | |
| `MAX_DIFF_CHARS` | `150000` | sem mudança |

Saída: o Markdown do comentário em `--output` e no stdout. Código de saída `0` em todos os casos em que um
comentário foi gerado, inclusive falhas do modelo (Constituição, Princípio III).

## Lista de modelos (novo)

```text
python reviewer/review.py --list-models [--test]
```

- Não exige `--base`.
- Saída: uma tabela em Markdown com `ID`, `Provedor`, `Nome`, `Acordo` e, com `--test`, `Chamada`.
- Sem permissão de leitura no Bedrock: a coluna `Acordo` mostra `desconhecido` e uma nota explica o motivo.
- Código de saída `0`.

## Workflow do GitHub

- `vars.MODEL_ID` (opcional) escolhe o modelo. Nenhuma mudança no YAML além da que já existe.
