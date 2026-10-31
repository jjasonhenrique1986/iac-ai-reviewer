<!--
Sync Impact Report
- Version change: template → 1.0.0 (primeira adoção)
- Princípios definidos: I. Sem credenciais fixas; II. Menor privilégio; III. A IA explica, não decide;
  IV. Saída validada; V. Testável sem AWS; VI. Documentação em português
- Seções adicionadas: Restrições de segurança e plataforma; Fluxo de desenvolvimento; Governance
- Seções removidas: nenhuma
- TODOs: nenhum
-->

# iac-ai-reviewer Constitution

## Core Principles

### I. Sem credenciais fixas

O revisor MUST acessar a AWS só com credenciais temporárias: OIDC no GitHub Actions e SSO
(IAM Identity Center) na máquina de quem desenvolve. Nenhuma access key, token de API ou senha
MAY ser exigida, gravada no repositório ou impressa em log. O ARN da role fica em secret do
repositório e o ID da conta é mascarado nos logs.

Racional: uma chave fixa vazada dá acesso até alguém perceber; credenciais temporárias expiram sozinhas.

### II. Menor privilégio

Cada projeto MUST ter a sua própria role IAM, com o nome baseado no nome do projeto, presa ao
repositório e aos eventos que o usam (claim `sub` exato, sem curingas). A política MUST liberar só
as ações e os modelos que o revisor chama. Liberar um modelo novo é uma mudança explícita de IAM,
nunca um curinga que cubra todos os modelos.

Racional: um repositório comprometido só alcança o que a role dele permite.

### III. A IA explica, não decide

A revisão MUST ser apenas um comentário no Pull Request. Ela NEVER aprova, bloqueia ou altera o PR,
e o job MUST NOT falhar por causa do conteúdo da revisão. Falhas do modelo (recusa, resposta
cortada, cota, acesso negado) MUST virar uma mensagem clara no comentário ou no log, nunca um
resultado inventado.

Racional: a decisão de merge é humana; a IA é apoio.

### IV. Saída validada

Toda resposta de modelo MUST ser validada contra o schema da revisão antes de ser publicada.
Resposta que não passa na validação é tratada como falha (Princípio III), não é publicada pela metade.
O diff MUST NOT ser cortado em silêncio: acima do limite, o revisor avisa e não chama o modelo.

Racional: um comentário com formato quebrado ou baseado em diff parcial engana quem revisa.

### V. Testável sem AWS

Toda funcionalidade MUST ter testes automatizados que rodam sem credenciais e sem rede da AWS
(servidor local ou dublês). Testes contra a AWS real são manuais e documentados, não fazem parte do CI.

Racional: o CI precisa rodar em qualquer fork e não pode gastar dinheiro nem depender de cota.

### VI. Documentação em português

README, mensagens do revisor, comentários no PR, specs e mensagens de commit MUST ser em português
do Brasil. Exemplos MUST usar valores fictícios (`111122223333`, `meu-usuario/meu-repo`), nunca IDs reais.

Racional: o projeto acompanha uma série de posts em português e é público.

## Restrições de segurança e plataforma

- Execução: GitHub Actions, só em PRs do próprio repositório (forks não recebem o token OIDC).
- Provedor de modelos: Amazon Bedrock, na região configurada (padrão `us-east-1`).
- Dependências fixadas por versão; actions do GitHub fixadas por tag de versão.
- State de qualquer IaC de apoio fica em `s3://terraform-projetos/<projeto>/`.

## Fluxo de desenvolvimento

- Toda mudança de comportamento segue o Spec Kit: `spec.md` → `plan.md` → `tasks.md` → implementação.
- Todo PR MUST passar em `pytest` antes do merge.
- Mudanças de IAM ficam no repositório de IaC (`aws-iam-baseline`, módulo `github-oidc-role`), não neste.

## Governance

Esta constituição prevalece sobre outras práticas do projeto. Emendas são feitas por PR que altera
este arquivo, com o motivo na descrição e a versão atualizada por semver: MAJOR para remover ou
redefinir um princípio, MINOR para adicionar princípio ou seção, PATCH para ajustes de texto.
Toda spec e todo plano MUST passar pelo "Constitution Check" do `plan.md` antes da implementação.

**Version**: 1.0.0 | **Ratified**: 2026-10-31 | **Last Amended**: 2026-10-31
