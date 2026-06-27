# Guia de Copy das Ofertas

Este documento registra as regras de formatação das mensagens geradas pelo `CopywriterAgent`.

## Decisao operacional atual para Shopee

Para o fluxo operacional principal da Shopee, a direcao atual e usar template
estatico preenchido por dados estruturados, sem depender de assistente para
redigir a mensagem base.

Motivo operacional:

- o `copy_briefs.json` ja contem os fatos necessarios para a mensagem;
- a rodada precisa ser previsivel, auditavel e reproduzivel;
- a mensagem da Shopee pode ser montada por preenchimento de placeholders,
  sem decisao linguistica aberta.

Leitura pratica:

- o template passa a ser a forma padrao de copy para Shopee;
- o assistente deixa de ser requisito para gerar o texto base;
- variacoes futuras podem existir, mas o caminho oficial atual e o template
  versionado.

Arquivos de referencia:

- template Shopee padrao: [`config/message_templates/shopee.txt`](../config/message_templates/shopee.txt)
- template legado do nicho `mae-e-bebe`: [`config/message_templates/mae-e-bebe.txt`](../config/message_templates/mae-e-bebe.txt)
- cupom global: [`config/coupon_urls.toml`](../config/coupon_urls.toml)
- preview HTML validado: [`tmp/mae-e-bebe-message-preview.html`](../tmp/mae-e-bebe-message-preview.html)

Template registrado para Shopee:

```text
🔥 {{facts.title}}

🏪 Loja: {{facts.marketplace}}

💵 {{facts.price | brl}}

🏷️ {{facts.discount_percent | round}}% OFF

⭐ Avaliação: {{facts.rating | rating_br}}/5

🎟️ Resgate o cupom desta página:
{{coupon_url}}

✅ Link do produto:
{{facts.url}}

Aviso: link de afiliado; podemos receber comissão pela compra. Preço e disponibilidade podem mudar.

(anúncio)
```

Contrato esperado de preenchimento:

- `facts.title`
- `facts.marketplace`
- `facts.price`
- `facts.discount_percent`
- `facts.rating`
- `facts.url`
- `coupon_url`

Validacao operacional desta etapa:

- o template foi testado com itens reais ja selecionados em
  `tmp/mae-e-bebe-copy-briefs-default.json`;
- foi gerado um mock HTML local para conferencia visual da mensagem final;
- a leitura visual foi aprovada como referencia inicial do formato Shopee.

Regra obrigatoria:

- o disclosure de afiliado faz parte do proprio template Shopee;
- `(anúncio)` sozinho nao substitui a exigencia de compliance;
- qualquer template estatico novo deve continuar trazendo aviso explicito de
  afiliado/comissao no corpo da mensagem.

## Linha de preço

Quando a oferta possui preço antigo maior que o preço atual, usar o formato:

```text
Preço: de R$ 89.90 por R$ 49.90 (44% OFF)
```

Motivo:

- comunica o preço original antes do preço final;
- deixa mais clara a economia para o usuário;
- padroniza a copy para Shopee, Amazon e demais marketplaces.

Quando não existir preço antigo válido, usar:

```text
Preço: R$ 49.90
```

Se houver desconto calculado, o percentual deve aparecer ao final entre parênteses:

```text
Preço: R$ 49.90 (20% OFF)
```

## Transparência de afiliado

Toda mensagem deve conter aviso claro de afiliado, por exemplo:

```text
Aviso: este é um link de afiliado; podemos receber comissão pela compra. Preço e disponibilidade podem mudar.
```

Essa regra é validada pelo `ComplianceAgent` e coberta pelos testes automatizados.
