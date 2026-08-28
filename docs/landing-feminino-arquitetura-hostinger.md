# Arquitetura TÃ©cnica â€” Landing Ofertas Femininas na Hostinger

**Status:** Definido para V1
**Data:** 2026-08-27
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir a arquitetura tÃ©cnica e o fluxo de deploy da landing `feminino` no domÃ­nio oficial do projeto.

DomÃ­nio de produÃ§Ã£o:

```text
https://mktdigitalofertas.com.br/
```

No momento desta decisÃ£o, o domÃ­nio estÃ¡ operacional e exibe apenas a pÃ¡gina padrÃ£o da hospedagem, sem aplicaÃ§Ã£o do projeto publicada.

## 2. Stack da V1

A implementaÃ§Ã£o da V1 utilizarÃ¡:

- HTML;
- CSS;
- JavaScript;
- PHP;
- `.htaccess` / `mod_rewrite` para URLs limpas;
- HTTPS/SSL;
- GitHub como origem versionada do cÃ³digo;
- pacote de deploy preparado a partir do cÃ³digo versionado;
- upload manual do pacote pelo hPanel/Gerenciador de Arquivos da Hostinger.

NÃ£o sÃ£o necessÃ¡rios para a V1:

- WordPress;
- Node.js;
- banco de dados;
- Supabase;
- VPS.

## 3. Capacidades confirmadas para o ambiente Hostinger Web Single

Segundo a validaÃ§Ã£o realizada no assistente da Hostinger para o plano Web Single, a soluÃ§Ã£o Ã© compatÃ­vel em geral com:

- HTML/CSS/JS;
- PHP;
- `.htaccess` e `mod_rewrite`;
- URLs limpas;
- redirects HTTP 302 em PHP;
- HTTPS/SSL;
- Gerenciador de Arquivos;
- FTP.

SFTP/Rsync nÃ£o fazem parte do Web Single.

ApÃ³s validaÃ§Ã£o prÃ¡tica do ambiente, foi confirmado que **nÃ£o serÃ¡ utilizado carregamento/deploy direto via GitHub no site atual**. Portanto, GitHub permanece como fonte de verdade e histÃ³rico do cÃ³digo, mas a publicaÃ§Ã£o na Hostinger serÃ¡ feita manualmente por pacote.

## 4. Fluxo oficial de versionamento e deploy

Fluxo definido para a V1:

```text
GitHub
  â†“
branch/revisÃ£o/commit aprovado
  â†“
geraÃ§Ã£o do pacote de produÃ§Ã£o
  â†“
validaÃ§Ã£o do conteÃºdo do pacote
  â†“
Hostinger hPanel / Gerenciador de Arquivos
  â†“
upload manual
  â†“
extraÃ§Ã£o/cÃ³pia para public_html
  â†“
testes pÃ³s-deploy
```

### 4.1 Papel do GitHub

GitHub continua sendo usado para:

- cÃ³digo-fonte oficial;
- histÃ³rico de alteraÃ§Ãµes;
- revisÃ£o;
- commits;
- rollback lÃ³gico;
- preparaÃ§Ã£o da versÃ£o que serÃ¡ empacotada.

A Hostinger nÃ£o Ã© a fonte de verdade do cÃ³digo.

### 4.2 Papel do pacote de deploy

A implementaÃ§Ã£o deve permitir gerar um pacote contendo **somente os arquivos necessÃ¡rios para produÃ§Ã£o**.

Estrutura conceitual do conteÃºdo do pacote:

```text
public_html/
â”œâ”€â”€ .htaccess
â”œâ”€â”€ feminino/
â”œâ”€â”€ assets/
â”œâ”€â”€ go/
â””â”€â”€ error/
```

O pacote nÃ£o deve exigir o upload do repositÃ³rio inteiro nem incluir documentaÃ§Ã£o, arquivos de desenvolvimento ou mÃ³dulos nÃ£o relacionados Ã  landing.

### 4.3 PublicaÃ§Ã£o manual

A publicaÃ§Ã£o serÃ¡ feita no hPanel, preferencialmente pelo Gerenciador de Arquivos, por meio de upload e extraÃ§Ã£o/cÃ³pia do pacote para `public_html` ou diretÃ³rio pÃºblico equivalente.

FTP pode ser usado como alternativa operacional se necessÃ¡rio.

NÃ£o hÃ¡ requisito de integraÃ§Ã£o automÃ¡tica GitHub â†’ Hostinger na V1.

## 5. URLs oficiais da V1

Landing feminina:

```text
https://mktdigitalofertas.com.br/feminino
```

Rota controlada para WhatsApp:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

A rota pÃºblica deve permanecer estÃ¡vel mesmo quando o grupo ou convite do WhatsApp mudar.

## 6. Arquitetura do redirect WhatsApp

Fluxo tÃ©cnico:

```text
/feminino
    â†“
HTML/CSS/JS
    â†“
CTA WhatsApp
    â†“
/go/whatsapp/feminino
    â†“
PHP
    â†“
configuraÃ§Ã£o centralizada do destino
    â†“
validaÃ§Ã£o
    â†“
HTTP 302
    â†“
convite atual do grupo WhatsApp
```

O convite real do grupo nÃ£o deve ser gravado diretamente no HTML ou JavaScript da landing enquanto for possÃ­vel manter essa separaÃ§Ã£o sem complexidade relevante.

O objetivo dessa separaÃ§Ã£o nÃ£o Ã© tornar o convite secreto. O endereÃ§o final poderÃ¡ ser observado pelo navegador durante o redirect. O objetivo Ã©:

- centralizar o destino;
- evitar duplicaÃ§Ã£o do convite;
- permitir troca do grupo sem editar a landing;
- manter anÃºncios, QR Codes, bio e URLs pÃºblicas estÃ¡veis;
- reduzir risco de links antigos permanecerem publicados.

Regra resumida:

> Centralizar o link, nÃ£o tentar escondÃª-lo.

## 7. ConfiguraÃ§Ã£o do convite

A V1 deve manter uma Ãºnica fonte de configuraÃ§Ã£o para o destino do nicho feminino.

A configuraÃ§Ã£o pode ser implementada em PHP, preferencialmente sem expor o valor no HTML ou JavaScript entregue ao navegador.

A localizaÃ§Ã£o exata do arquivo/configuraÃ§Ã£o deve seguir a soluÃ§Ã£o mais simples suportada pelo ambiente Hostinger e pelo processo de pacote manual.

NÃ£o Ã© requisito criar infraestrutura adicional apenas para proteger esse valor.

Ao gerar o pacote de deploy, a configuraÃ§Ã£o necessÃ¡ria para produÃ§Ã£o deve estar claramente documentada. Se o arquivo de configuraÃ§Ã£o nÃ£o for versionado com o convite real, o processo deve indicar exatamente onde inserir o valor antes ou depois do upload.

## 8. Estrutura de arquivos de referÃªncia

Estrutura conceitual compatÃ­vel com a hospedagem:

```text
public_html/
â”œâ”€â”€ feminino/
â”‚   â””â”€â”€ index.html
â”œâ”€â”€ assets/
â”‚   â”œâ”€â”€ css/
â”‚   â”œâ”€â”€ js/
â”‚   â”œâ”€â”€ img/
â”‚   â””â”€â”€ qr/
â”œâ”€â”€ go/
â”‚   â””â”€â”€ whatsapp/
â”‚       â””â”€â”€ feminino.php
â”œâ”€â”€ error/
â”‚   â””â”€â”€ whatsapp-indisponivel.html
â””â”€â”€ .htaccess

configuraÃ§Ã£o do WhatsApp
â””â”€â”€ fonte Ãºnica utilizada pelo PHP
```

A estrutura final pode ser ajustada durante a implementaÃ§Ã£o desde que preserve os contratos de URL, a fonte Ãºnica de configuraÃ§Ã£o e a possibilidade de gerar um pacote simples para upload manual.

## 9. QR Code no desktop

A versÃ£o desktop da landing deve poder exibir um QR Code como alternativa ao botÃ£o de WhatsApp.

O QR Code deve apontar para a URL controlada do projeto:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

O QR Code nÃ£o deve apontar diretamente para `chat.whatsapp.com`.

Motivo:

```text
QR Code permanente
      â†“
/go/whatsapp/feminino
      â†“
destino configurÃ¡vel
      â†“
grupo atual
```

Assim, trocar o grupo ou o convite nÃ£o exige gerar ou redistribuir um novo QR Code.

### 9.1 Comportamento por dispositivo

**Mobile**

Priorizar o CTA:

> Quero receber as ofertas no WhatsApp

**Desktop**

Pode apresentar simultaneamente:

- CTA de WhatsApp;
- QR Code para abrir a mesma rota controlada no celular.

O QR Code Ã© um recurso complementar e nÃ£o substitui o CTA principal.

## 10. UTM e QR Code

Os CTAs originados de uma landing acessada com UTMs devem preservar os parÃ¢metros conforme o contrato V1.

O QR Code institucional fixo pode utilizar a rota limpa sem UTM:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Caso no futuro existam QR Codes especÃ­ficos por campanha, eles poderÃ£o apontar para a mesma rota com UTMs prÃ³prias, sem alterar a arquitetura.

## 11. Estado atual do domÃ­nio

Estado informado em 2026-08-27:

- domÃ­nio: `mktdigitalofertas.com.br`;
- domÃ­nio operacional;
- pÃ¡gina atual: pÃ¡gina padrÃ£o/vazia da hospedagem;
- aplicaÃ§Ã£o da landing ainda nÃ£o implantada.

Esse estado permite que a primeira publicaÃ§Ã£o da landing seja tratada como implantaÃ§Ã£o inicial, sem necessidade de migraÃ§Ã£o de uma aplicaÃ§Ã£o existente do projeto.

## 12. PreparaÃ§Ã£o antes do primeiro deploy

Antes da publicaÃ§Ã£o manual:

1. confirmar que o SSL do domÃ­nio estÃ¡ ativo;
2. abrir `public_html` e registrar o conteÃºdo existente antes de substituir qualquer arquivo;
3. gerar o pacote de produÃ§Ã£o a partir de uma versÃ£o/commit aprovado no GitHub;
4. validar que o pacote contÃ©m somente os arquivos necessÃ¡rios Ã  landing;
5. validar onde ficarÃ¡ a configuraÃ§Ã£o centralizada do convite;
6. manter backup simples dos arquivos atuais da pÃ¡gina padrÃ£o caso seja necessÃ¡rio rollback;
7. fazer upload do pacote no hPanel;
8. extrair/copiar os arquivos para `public_html`;
9. executar o checklist pÃ³s-deploy.

## 13. Regras do pacote de produÃ§Ã£o

O pacote deve:

- poder ser extraÃ­do diretamente ou copiado de forma simples para `public_html`;
- conter a estrutura necessÃ¡ria para `/feminino` e `/go/whatsapp/feminino`;
- incluir `.htaccess` quando necessÃ¡rio;
- incluir PHP, CSS, JS, imagens e QR Code necessÃ¡rios;
- nÃ£o incluir `.git`;
- nÃ£o incluir documentaÃ§Ã£o do projeto;
- nÃ£o incluir arquivos de teste/desenvolvimento desnecessÃ¡rios;
- nÃ£o incluir outros mÃ³dulos do repositÃ³rio;
- possuir instruÃ§Ãµes curtas de configuraÃ§Ã£o e publicaÃ§Ã£o.

A geraÃ§Ã£o do pacote deve ser reproduzÃ­vel a partir do repositÃ³rio.

## 14. Rollback operacional

Como o deploy Ã© manual, o rollback da V1 deve ser simples:

1. manter o commit/tag ou referÃªncia da versÃ£o anterior no GitHub;
2. manter, quando aplicÃ¡vel, uma cÃ³pia do pacote anterior;
3. em caso de falha, reenviar o pacote anterior ou restaurar o backup dos arquivos substituÃ­dos;
4. testar novamente as URLs principais.

## 15. CritÃ©rios de aceite tÃ©cnico

A arquitetura desta etapa serÃ¡ considerada implementada quando:

1. `https://mktdigitalofertas.com.br/feminino` carregar a landing;
2. HTML/CSS/JS forem servidos via HTTPS;
3. `/go/whatsapp/feminino` executar o fluxo PHP de redirect;
4. o redirect usar HTTP 302;
5. o convite nÃ£o estiver hardcoded no HTML/JS da landing;
6. houver uma Ãºnica fonte de configuraÃ§Ã£o do destino;
7. trocar o destino nÃ£o exigir alteraÃ§Ã£o da landing;
8. o QR Code desktop apontar para `/go/whatsapp/feminino`;
9. o botÃ£o mobile e o QR Code desktop chegarem ao mesmo destino lÃ³gico;
10. o cÃ³digo publicado estiver versionado no GitHub;
11. existir um pacote de produÃ§Ã£o limpo e reproduzÃ­vel;
12. o deploy puder ser executado manualmente pelo hPanel sem enviar o repositÃ³rio inteiro;
13. existir checklist de publicaÃ§Ã£o e pÃ³s-deploy.

## 16. PrÃ³xima etapa

A especificaÃ§Ã£o tÃ©cnica de implementaÃ§Ã£o deve usar este fluxo de deploy manual como contrato operacional e exigir do Codex a criaÃ§Ã£o de um pacote pronto para upload na Hostinger.
