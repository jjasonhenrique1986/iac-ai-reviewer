# Feature Specification: Seleção do modelo de IA

**Feature Branch**: `sdd-selecao-de-modelo`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Permita que o usuário escolha o modelo que ele quer utilizar ou crie uma lista
com os modelos disponíveis. A role usada nos testes deve ter o nome baseado no nome do projeto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher o modelo da revisão (Priority: P1)

Quem mantém o repositório escolhe, pela configuração do repositório, qual modelo de IA faz a revisão
dos Pull Requests, entre os modelos suportados pelo revisor (da Anthropic e de outros provedores
disponíveis no Amazon Bedrock, como os modelos abertos da OpenAI). A troca não exige mudar código.

**Why this priority**: hoje o revisor só funciona com os modelos Claude. Se a conta não tem acesso ou
cota para eles, o revisor fica inutilizável. Poder escolher outro modelo resolve isso imediatamente.

**Independent Test**: configurar o repositório para um modelo suportado diferente do padrão, abrir um
PR com mudança em Terraform e verificar que o comentário de revisão foi gerado por esse modelo.

**Acceptance Scenarios**:

1. **Given** nenhum modelo configurado, **When** um PR é aberto, **Then** a revisão usa o modelo padrão
   (Claude Opus 5.5), como hoje.
2. **Given** o repositório configurado com um modelo suportado de outro provedor, **When** um PR é
   aberto, **Then** a revisão é gerada por esse modelo, com o mesmo formato de comentário, e o rodapé
   informa qual modelo foi usado.
3. **Given** o repositório configurado com um modelo fora da lista de suportados, **When** um PR é
   aberto, **Then** o modelo não é chamado e o comentário explica que o modelo não é suportado e lista
   os modelos aceitos.

---

### User Story 2 - Ver quais modelos estão disponíveis (Priority: P2)

Quem configura o revisor consulta a lista de modelos suportados e descobre quais deles estão realmente
liberados para a sua conta e região, antes de escolher.

**Why this priority**: o Bedrock mostra modelos no catálogo que a conta não consegue usar (acordo não
aceito, cota zerada). Sem essa lista, a pessoa só descobre o problema depois de abrir um PR.

**Independent Test**: rodar a consulta de modelos com credenciais de leitura e conferir que cada modelo
suportado aparece com o seu status de disponibilidade.

**Acceptance Scenarios**:

1. **Given** credenciais com permissão de leitura no Bedrock, **When** a pessoa pede a lista de
   modelos, **Then** vê todos os modelos suportados, com provedor, identificador e se estão liberados
   para a conta na região.
2. **Given** credenciais sem permissão de leitura no Bedrock, **When** a pessoa pede a lista,
   **Then** vê a lista de modelos suportados com o status "desconhecido" e uma explicação do motivo.

---

### User Story 3 - Entender por que o modelo escolhido falhou (Priority: P3)

Quando o modelo escolhido não responde (acesso negado, cota zerada, recusa, resposta fora do formato),
o comentário do PR diz o que aconteceu e o que fazer, em vez de o job quebrar sem explicação.

**Why this priority**: sem isso, a pessoa precisa abrir os logs do Actions para entender um erro de
acesso ou de cota, como aconteceu nos primeiros testes.

**Independent Test**: simular cada tipo de falha com um servidor local e verificar a mensagem do comentário.

**Acceptance Scenarios**:

1. **Given** um modelo sem acesso liberado para a conta, **When** a revisão roda, **Then** o comentário
   informa que o modelo não está disponível para a conta e sugere conferir o acesso e as cotas no Bedrock.
2. **Given** uma resposta do modelo que não segue o formato da revisão, **When** a revisão roda,
   **Then** nada parcial é publicado e o comentário informa que a resposta não pôde ser interpretada.

---

### Edge Cases

- O modelo configurado existe no Bedrock mas não está na lista de suportados: tratado como não suportado.
- O valor configurado está vazio: usa o modelo padrão.
- O modelo de reserva para recusas só se aplica a modelos que têm esse mecanismo (Claude); para os
  demais, uma recusa é relatada no comentário.
- O diff passa do limite de tamanho: o comportamento atual se mantém (avisa e não chama o modelo),
  qualquer que seja o modelo.
- O modelo não existe na região configurada: tratado como indisponível, com mensagem clara.
- A role do GitHub não tem permissão para o modelo escolhido: tratado como acesso negado, com a dica de
  liberar o modelo na política da role.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O revisor MUST permitir escolher o modelo pela configuração do repositório, sem mudança de código.
- **FR-002**: O revisor MUST manter uma lista de modelos suportados, com identificador, provedor e nome
  legível, documentada no README.
- **FR-003**: O revisor MUST usar o Claude Opus 5.5 quando nenhum modelo for configurado.
- **FR-004**: O revisor MUST recusar, antes de qualquer chamada, um modelo fora da lista de suportados,
  informando no comentário os modelos aceitos.
- **FR-005**: O revisor MUST oferecer uma forma de listar os modelos suportados com o status de
  disponibilidade na conta e região de quem consulta.
- **FR-006**: Toda resposta, de qualquer modelo, MUST ser validada contra o mesmo formato de revisão antes
  de ser publicada (Constituição, Princípio IV).
- **FR-007**: O revisor MUST manter o modelo de reserva para recusas nos modelos que suportam esse
  mecanismo e MUST relatar a recusa nos demais.
- **FR-008**: O rodapé do comentário MUST informar o modelo que gerou a revisão.
- **FR-009**: Falhas de acesso, cota, recusa ou formato MUST virar uma mensagem clara no comentário, sem
  falhar o job por causa do conteúdo (Constituição, Princípio III).
- **FR-010**: A documentação MUST explicar que cada modelo escolhido precisa estar liberado na política
  da role do projeto, e a role de testes local MUST ter o nome baseado no nome do projeto
  (Constituição, Princípio II).

### Key Entities

- **Modelo suportado**: um modelo que o revisor sabe chamar. Atributos: identificador no Bedrock,
  provedor, nome legível, se tem modelo de reserva para recusas.
- **Status de disponibilidade**: para um modelo suportado, numa conta e região: liberado, não liberado
  (com o motivo, quando conhecido) ou desconhecido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trocar o modelo da revisão leva menos de 1 minuto e não exige commit de código.
- **SC-002**: 100% das revisões publicadas passam na validação de formato, para todos os modelos suportados.
- **SC-003**: A consulta de modelos mostra o status de todos os modelos suportados em menos de 30 segundos.
- **SC-004**: Em 100% das falhas de modelo simuladas nos testes, o comentário identifica o tipo de falha
  sem precisar abrir os logs.

## Assumptions

- Todos os modelos são acessados pelo Amazon Bedrock, com as mesmas credenciais temporárias de hoje (OIDC no
  GitHub, SSO local). Outros provedores fora do Bedrock estão fora do escopo.
- Lista inicial de suportados: Claude Opus 5.5 (padrão), Claude Opus 4.8 (reserva), OpenAI gpt-oss-120b e
  OpenAI gpt-oss-20b. Estes dois últimos foram os únicos modelos de texto da OpenAI liberados para a conta
  em 2026-10-31, e o gpt-oss-120b já gerou uma revisão válida num teste manual.
- A permissão para cada modelo é concedida na role do projeto, no repositório de IaC (`aws-iam-baseline`),
  fora deste repositório.
- A role/permission set usado nos testes locais passa a ter o nome do projeto (por exemplo,
  `IacAiReviewer`) em vez de um nome genérico.
- A consulta de disponibilidade usa permissões de leitura do Bedrock; o workflow do PR não precisa delas.
