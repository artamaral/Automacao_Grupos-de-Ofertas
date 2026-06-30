# Diretrizes de Mídia

Este documento define como o projeto deve tratar imagens, vídeos e outros criativos usados nas mensagens de oferta.

## Objetivo

Garantir que cada oferta tenha mídia adequada sem depender de processo manual frágil ou de arquivos sem rastreabilidade.

## Estratégia atual

A mídia deve seguir esta ordem de preferência:

1. Mídia informada pela própria fonte da oferta.
2. Mídia mapeada manualmente em catálogo curado.
3. Fallback para imagem válida do produto.
4. Bloqueio da oferta, quando a saída exigir mídia e nenhuma mídia válida existir.

## Imagens

Imagens devem ser usadas quando vierem de fonte permitida ou do próprio marketplace/provider.

Regras:

- não inventar imagem;
- não usar imagem vazia;
- validar URL quando aplicável;
- manter vínculo com a oferta original;
- não baixar nem versionar grandes arquivos sem necessidade.

## Vídeos

Vídeos devem ser tratados como mapeamento opcional e controlado.

Modelo recomendado:

```text
produto/link -> media_id -> arquivo local ou referência controlada
```

Exemplo de campos em catálogo curado:

```text
offer_id, marketplace, link, title, media_id, media_type
```

## Arquivos locais de mídia

Arquivos locais grandes não devem ser versionados no GitHub sem decisão explícita.

Locais sugeridos para uso local:

```text
.data/media/
.data/media/videos/
.data/media/images/
```

## Nome de mídia local

Quando houver arquivo local, preferir nomes previsíveis:

```text
<marketplace>_<offer_id>_<media_id>.mp4
<marketplace>_<offer_id>_<media_id>.jpg
```

## Fallback

Se uma oferta não tiver vídeo, a imagem do produto pode ser usada como fallback quando a origem for confiável.

Se não houver imagem nem vídeo válido, a oferta deve ser bloqueada para saídas que dependam de mídia.

## Relação com specs

Qualquer automação nova de mídia deve ter spec própria, indicando:

- entrada;
- saída;
- formato de mapeamento;
- onde arquivos ficam;
- comportamento quando a mídia não existe;
- testes esperados.
