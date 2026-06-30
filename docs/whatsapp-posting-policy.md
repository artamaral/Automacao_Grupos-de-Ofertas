# Política de Postagem em Canais e Grupos

Este documento define a política operacional para preparação e eventual publicação de mensagens em canais próprios ou autorizados.

## Objetivo

Manter o projeto seguro, auditável e respeitoso com usuários, plataformas e regras de consentimento.

## Escopo atual

Na fase atual, o projeto deve preparar mensagens e artefatos locais em `dry-run`. Publicação real não é o caminho padrão.

## Princípios

- Enviar apenas para grupos, canais ou comunidades próprios ou explicitamente autorizados.
- Trabalhar com entrada voluntária e consentimento claro.
- Não fazer spam.
- Não enviar para contatos ou grupos não cadastrados.
- Não criar automação para burlar política, limite ou detecção de plataforma.
- Não ativar publicação real sem aprovação humana, logs e configuração explícita.

## Travas obrigatórias

A publicação real só pode ser considerada quando todas as condições forem verdadeiras:

```text
ENABLE_REAL_PUBLISH=true
canal permitido
mensagem aprovada
logs habilitados
provider permitido/configurado
```

Se qualquer condição falhar, o comportamento deve ser bloqueio ou dry-run.

## Fila de postagem

Quando existir publicação real no futuro, ela deve usar fila controlada.

Regras esperadas:

- uma publicação por vez;
- limite diário configurável;
- logs de mensagem, canal, horário e status;
- revisão humana antes de envio;
- falhas explícitas e rastreáveis;
- nenhuma tentativa silenciosa de reenvio em massa.

## Conteúdo das mensagens

Toda mensagem deve passar por compliance antes de publicação.

Bloqueios mínimos:

- sem aviso de afiliado;
- sem link;
- preço inválido;
- promessa falsa;
- urgência inventada;
- origem incorreta;
- canal não permitido.

## Credenciais e sessões

Nunca versionar:

- QR code;
- sessão local;
- token;
- cookie;
- chave de API;
- arquivo `.env` real;
- credencial de marketplace;
- credencial de canal.

## Relação com automação

O fluxo final pode ser chamado por orquestrador/agendador, mas deve manter revisão, travas e logs.

Automação aceitável:

```text
preparar fila -> gerar mensagens -> revisar -> consolidar aprovadas
```

Automação que permanece fora do padrão atual:

```text
gerar oferta -> publicar automaticamente sem aprovação
```

## Testes esperados

Quando houver código de publicação, deve existir teste para:

- bloqueio com `ENABLE_REAL_PUBLISH=false`;
- bloqueio sem aprovação humana;
- bloqueio de canal não permitido;
- saída dry-run como padrão.
