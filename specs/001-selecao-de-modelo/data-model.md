# Data Model: Seleção do modelo de IA

## SupportedModel

Um modelo que o revisor sabe chamar. Imutável, definido no código.

| Campo | Tipo | Regra |
|---|---|---|
| `model_id` | texto | ID do modelo no Bedrock; único na lista |
| `provider` | `anthropic` \| `openai` | define o cliente usado |
| `name` | texto | nome legível, usado no README e no `--list-models` |
| `api` | `mantle` \| `converse` | `anthropic` → `mantle`; `openai` → `converse` |

Lista inicial:

| `model_id` | `provider` | `api` |
|---|---|---|
| `anthropic.claude-opus-5-5` (padrão) | anthropic | mantle |
| `anthropic.claude-opus-4-8` (reserva padrão) | anthropic | mantle |
| `openai.gpt-oss-120b-1:0` | openai | converse |
| `openai.gpt-oss-20b-1:0` | openai | converse |

Validação na escolha (`MODEL_ID`):

- vazio → `anthropic.claude-opus-5-5`;
- fora da lista → falha "modelo não suportado", sem chamar o Bedrock;
- `FALLBACK_MODEL_ID` continua aceito para modelos `mantle` e deve estar na lista.

## AvailabilityStatus

Resultado do `--list-models` para um modelo numa conta e região.

| Campo | Valores |
|---|---|
| `agreement` | `AVAILABLE`, `PENDING`, `NOT_AVAILABLE`, `ERROR` ou `desconhecido` |
| `call` (só com `--test`) | `ok`, ou o tipo de erro (acesso negado, não encontrado, limite) |

## Review (existente, sem mudança)

`summary`, `risk` (`alto`/`medio`/`baixo`), `findings[]` com `file`, `severity`, `title`, `explanation`,
`suggestion`. Para o Converse, o schema é enviado expandido (ver research.md, item 2).
