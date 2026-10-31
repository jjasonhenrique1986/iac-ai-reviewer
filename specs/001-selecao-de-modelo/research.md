# Research: Seleção do modelo de IA

Testes feitos em 2026-10-31 na conta do projeto, região `us-east-1`.

## 1. Como chamar modelos que não são Claude

- **Decision**: API Converse do Bedrock (`bedrock-runtime`, via `boto3`) para os modelos `openai.gpt-oss-*`.
  Os modelos Claude continuam no `AnthropicBedrockMantle`, sem mudança.
- **Rationale**: o SDK da Anthropic só fala com modelos Claude. O Converse é a API do próprio Bedrock,
  usa as mesmas credenciais temporárias (OIDC/SSO) e já está disponível pelo `boto3`, que o
  `anthropic[bedrock]` instala. Teste manual: o `gpt-oss-120b` gerou uma revisão válida pelo Converse.
- **Alternatives considered**: SDK da OpenAI apontando para um endpoint compatível do Bedrock (mais uma
  dependência e outro modelo de credenciais); trocar tudo para o Converse, inclusive o Claude (perde a saída
  estruturada nativa e o fallback de recusa do SDK da Anthropic).

## 2. Saída estruturada nos modelos gpt-oss

- **Decision**: ferramenta forçada (`toolChoice: {"tool": ...}`) cujo `inputSchema` é o schema `Review`
  **expandido** (sem `$ref`/`$defs`, sem anotações `title`, com `additionalProperties: false`), seguida de
  validação Pydantic. Se a resposta não trouxer a ferramenta ou não validar, uma nova tentativa; se falhar de
  novo, mensagem de falha no comentário.
- **Rationale**: com o schema original (com `$ref`), 6 de 6 respostas vieram com campos inventados nos
  achados. Com o schema expandido: `gpt-oss-120b` 3/3 válidas; `gpt-oss-20b` 2/3 (uma sem chamar a
  ferramenta). Uma nova tentativa cobre o caso observado.
- **Alternatives considered**: pedir JSON no prompt e extrair do texto (funcionou uma vez, mas sem garantia
  de schema); `toolChoice: any` (mesmo resultado do forçado, sem vantagem).

## 3. Lista de modelos suportados e status

- **Decision**: lista fechada no código (`SUPPORTED_MODELS`). A opção `--list-models` mostra cada modelo com
  o status do acordo (`GetFoundationModelAvailability`). Com `--test`, faz também uma chamada mínima a cada
  modelo para provar que ele responde.
- **Rationale**: o acordo `AVAILABLE` não garante uso: em 2026-10-31 o Claude Opus 5.5 tinha acordo aceito e
  ainda respondia 403 por cota zerada. Só uma chamada real confirma. Lista fechada atende ao Princípio II.
- **Alternatives considered**: listar todo o catálogo do Bedrock (mostra modelos que o revisor não sabe
  chamar); consultar o Service Quotas (nomes de cota variam por modelo e endpoint, frágil).

## 4. Erros e mensagens

- **Decision**: mapear erros para mensagens do comentário:

  | Origem | Erro | Mensagem |
  |---|---|---|
  | Mantle | 403 `PermissionDeniedError` | modelo não disponível para a conta (acesso, acordo ou cota) |
  | Mantle | 404 `NotFoundError` | modelo não existe nesse endpoint/região |
  | Converse | `AccessDeniedException` | sem acesso: conta (acordo/cota) ou política da role |
  | Converse | `ResourceNotFoundException` / `ValidationException` de modelo | modelo não existe na região |
  | Converse | `ThrottlingException` | limite de uso atingido, tente de novo |
  | Ambos | recusa / sem ferramenta / schema inválido | já existentes, reaproveitados |

- **Rationale**: Princípio III. O AccessDenied do Converse não diferencia IAM de acordo, então a mensagem
  cita as duas causas.

## 5. Permissões

- **Decision**:
  - Role do GitHub (`gh-iac-ai-reviewer`): manter `bedrock-mantle:CreateInference` e adicionar
    `bedrock:InvokeModel` só nos ARNs `foundation-model/openai.gpt-oss-120b-1:0` e `openai.gpt-oss-20b-1:0`.
  - Permission set local com o nome do projeto, `IacAiReviewer` (sessão de 1 h): as mesmas ações de
    inferência e `bedrock:GetFoundationModelAvailability` para o `--list-models`. Perfil `iac-ai-reviewer`
    no `~/.aws/config`.
- **Rationale**: Princípio II. O Converse exige `bedrock:InvokeModel` no ARN do modelo.
