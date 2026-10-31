# iac-ai-reviewer (arquivado)

Este projeto virou uma **action reutilizável** e o código, com todo o histórico de commits, mudou
para **[github-actions/iac-ai-review](https://github.com/jjasonhenrique1986/github-actions/tree/main/iac-ai-review)**.

Para usar a revisão de Pull Requests de Terraform e Kubernetes com IA no seu repositório, crie um
workflow com a action:

```yaml
- uses: actions/checkout@v7
  with:
    fetch-depth: 0
- uses: jjasonhenrique1986/github-actions/iac-ai-review@v1
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
```

O passo a passo completo (role IAM, modelos, exemplos e segurança) está no
[README da action](https://github.com/jjasonhenrique1986/github-actions/tree/main/iac-ai-review#readme).

Este repositório fica arquivado, somente leitura, para os links antigos continuarem funcionando.
