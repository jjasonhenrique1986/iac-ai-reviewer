# iac-ai-reviewer

Revisão automática de Pull Requests de infraestrutura (Terraform e Kubernetes)
com **IA no Amazon Bedrock** (Claude ou OpenAI gpt-oss), rodando no **GitHub Actions**
sem access keys.

A cada PR o workflow:

1. Roda o **checkov** no repositório, para ter achados determinísticos.
2. Assume uma role IAM via **OIDC** (credenciais temporárias).
3. Envia o diff dos arquivos `.tf`, `.tfvars`, `.yaml` e `.yml` e a saída do
   checkov para o modelo escolhido, que devolve uma revisão em **JSON validado** (Pydantic).
4. Publica a revisão como comentário no PR, atualizando o mesmo comentário a cada push.

A IA explica os riscos. Ela **não aprova nem bloqueia** o PR.

## Estrutura

```
.github/workflows/ai-review.yml   workflow do GitHub Actions
reviewer/review.py                script que monta o prompt, chama o modelo e gera o Markdown
iam/trust-policy.json             trust policy da role (OIDC do GitHub)
iam/bedrock-policy.json           permissão para chamar os modelos no Bedrock
specs/                            especificações (Spec Kit)
examples/                         Terraform e manifest K8s com problemas, para testar
tests/                            testes sem AWS (um servidor local simula o Bedrock)
```

## Configuração

### 1. Escolha do modelo

O revisor aceita estes modelos do Amazon Bedrock:

| `MODEL_ID` | Provedor | Observação |
|---|---|---|
| `anthropic.claude-opus-5-5` | Anthropic | padrão |
| `anthropic.claude-opus-4-8` | Anthropic | reserva padrão para recusas do Claude |
| `openai.gpt-oss-120b-1:0` | OpenAI | modelo aberto |
| `openai.gpt-oss-20b-1:0` | OpenAI | modelo aberto, menor e mais barato |

Um `MODEL_ID` fora da lista não é chamado: o comentário explica e mostra os modelos aceitos.
Os modelos Claude usam o SDK da Anthropic (saída estruturada nativa e modelo reserva para
recusas). Os gpt-oss usam a API Converse do Bedrock, com uma ferramenta forçada cujo input é
a revisão; se a resposta não seguir o formato, o revisor tenta mais uma vez.

Para ver quais estão liberados na sua conta:

```bash
python reviewer/review.py --list-models          # status do acordo de cada modelo
python reviewer/review.py --list-models --test   # e uma chamada mínima a cada um
```

O acordo aceito não garante uso: a cota do modelo também precisa ser maior que zero.
Use `--test` para ter certeza. Para liberar um modelo, aceite o acesso em
**Amazon Bedrock → Model catalog** e confira as cotas em **Service Quotas → Amazon Bedrock**.

### 2. Role IAM

O identity provider do GitHub precisa estar cadastrado no IAM (uma vez por conta).
A política em `iam/bedrock-policy.json` libera os modelos da lista; deixe só os que você usa.
Os Claude precisam de `bedrock-mantle:CreateInference`; os gpt-oss, de `bedrock:InvokeModel`
no ARN de cada modelo.
Troque `111122223333` e `meu-usuario/meu-repo` nos arquivos de `iam/` e crie a role:

```bash
aws iam create-role \
  --role-name github-iac-ai-reviewer \
  --assume-role-policy-document file://iam/trust-policy.json

aws iam put-role-policy \
  --role-name github-iac-ai-reviewer \
  --policy-name bedrock-claude \
  --policy-document file://iam/bedrock-policy.json
```

O `sub` da trust policy é `repo:meu-usuario/meu-repo:pull_request`, ou seja, só
workflows disparados por pull requests desse repositório assumem a role.

> **Confira o formato do `sub` no seu repositório.** Se o repositório usa o
> *subject imutável*, o `sub` inclui os IDs numéricos do dono e do repositório,
> como `repo:meu-usuario@123456/meu-repo@7891011:pull_request`, e a trust
> policy acima recusa o token (`Not authorized to perform
> sts:AssumeRoleWithWebIdentity`). Para ver o prefixo que o GitHub usa:
>
> ```bash
> gh api repos/meu-usuario/meu-repo/actions/oidc/customization/sub --jq .sub_claim_prefix
> ```
>
> Na trust policy, use esse prefixo seguido de `:pull_request`.

### 3. Secret e variáveis do repositório

Em **Settings → Secrets and variables → Actions**:

| Nome | Tipo | Obrigatório | Exemplo |
|---|---|---|---|
| `AWS_ROLE_ARN` | Secret | sim | `arn:aws:iam::111122223333:role/github-iac-ai-reviewer` |
| `AWS_REGION` | Variable | não (padrão `us-east-1`) | `us-east-1` |
| `MODEL_ID` | Variable | não (padrão `anthropic.claude-opus-5-5`) | `openai.gpt-oss-120b-1:0` |

A autenticação é toda por OIDC, sem access keys. O ARN da role não é uma
credencial: ele fica como secret só para o ID da conta não aparecer no
repositório nem nos logs.

## Rodando localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt checkov

pytest                       # testes, sem chamar a AWS

checkov -d . --framework terraform kubernetes --compact --quiet --soft-fail > checkov.txt
python reviewer/review.py --base origin/main --checkov checkov.txt   # usa suas credenciais AWS
```

Outras variáveis aceitas pelo script: `FALLBACK_MODEL_ID` e `MAX_DIFF_CHARS`
(padrão 150000). Se o diff passar do limite, o script **não corta o conteúdo**:
ele avisa no comentário e não chama o modelo.

## Segurança

- **PRs de forks não são revisados.** O GitHub não entrega o token OIDC para eles,
  e o job é pulado.
- **O diff é tratado como dado não confiável.** Ele vai dentro de tags `<diff>`, e o
  prompt manda ignorar instruções que apareçam ali. Isso reduz, mas não elimina, o
  risco de prompt injection. Por isso o job só tem permissão para ler o código e
  comentar no PR.
- **Use `pull_request`, nunca `pull_request_target`**, para não rodar código do PR
  com permissões do repositório base.
- **O conteúdo do PR vai para o Bedrock.** Confira a política da sua empresa antes
  de usar em repositórios com dados sensíveis.
