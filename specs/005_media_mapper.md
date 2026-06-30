# SPEC 005 — Mapeamento de Mídia

Status: Rascunho

## Objetivo

Definir como associar imagens ou vídeos a ofertas sem deixar arquivos soltos, sem inventar mídia e sem depender de processo manual não rastreável.

## Contexto

O projeto pode usar imagem do marketplace como fallback e, futuramente, mapear vídeos curados por produto ou por oferta.

## Entrada

Possíveis entradas:

- oferta normalizada com `image_url`;
- catálogo curado com `media_id`;
- arquivo local em `.data/media/`;
- referência externa controlada;
- tipo de mídia desejado.

Campos sugeridos:

```text
offer_id
marketplace
url
image_url
media_id
media_type
media_path
```

## Saída

Oferta ou mensagem enriquecida com referência de mídia válida.

## Regras obrigatórias

- Não inventar mídia.
- Não exigir vídeo quando imagem válida for suficiente para a etapa atual.
- Usar imagem do produto como fallback quando confiável.
- Bloquear saída que exige mídia se não houver mídia válida.
- Não versionar arquivos grandes de mídia sem decisão explícita.
- Preservar rastreabilidade entre oferta e mídia.

## Locais locais sugeridos

```text
.data/media/videos/
.data/media/images/
```

## Nome de arquivo local

Formato recomendado:

```text
<marketplace>_<offer_id>_<media_id>.mp4
<marketplace>_<offer_id>_<media_id>.jpg
```

## Fora de escopo

- Criação automática de vídeos.
- Download massivo de mídia.
- Publicação real.
- Uso de mídia sem direito ou origem confiável.

## Critérios de aceite

- Oferta com `image_url` válido pode seguir com imagem.
- Oferta com `media_id` e arquivo local existente pode usar o arquivo.
- Oferta sem mídia é bloqueada quando a saída exigir mídia.
- Arquivos locais permanecem fora do Git quando forem artefatos de execução.

## Testes esperados

- Teste de fallback para `image_url`.
- Teste de mapeamento por `media_id`.
- Teste de bloqueio quando arquivo não existe.
- Teste de formato de caminho local.

## Harness / validação local

A validação deve ocorrer dentro do fluxo local dry-run, sem publicação real:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```
