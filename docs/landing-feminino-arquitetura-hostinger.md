# Arquitetura Técnica — Landing Ofertas Femininas na Hostinger

**Status:** Definido para V1  
**Data:** 2026-08-27  
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir a arquitetura técnica e o fluxo de deploy da landing `feminino` no domínio oficial do projeto.

Domínio de produção:

```text
https://mktdigitalofertas.com.br/
```

No momento desta decisão, o domínio está operacional e exibe apenas a página padrão da hospedagem, sem aplicação do projeto publicada.

## 2. Stack da V1

A implementação da V1 utilizará:

- HTML;
- CSS;
- JavaScript;
- PHP;
- `.htaccess` / `mod_rewrite` para URLs limpas;
- HTTPS/SSL;
- GitHub como origem versionada do código;
- pacote de deploy preparado a partir do código versionado;
- upload manual do pacote pelo hPanel/Gerenciador de Arquivos da Hostinger.

Não são necessários para a V1:

- WordPress;
- Node.js;
- banco de dados;
- Supabase;
- VPS.

## 3. Capacidades confirmadas para o ambiente Hostinger Web Single

Segundo a validação realizada no assistente da Hostinger para o plano Web Single, a solução é compatível em geral com:

- HTML/CSS/JS;
- PHP;
- `.htaccess` e `mod_rewrite`;
- URLs limpas;
- redirects HTTP 302 em PHP;
- HTTPS/SSL;
- Gerenciador de Arquivos;
- FTP.

SFTP/Rsync não fazem parte do Web Single.

Após validação prática do ambiente, foi confirmado que **não será utilizado carregamento/deploy direto via GitHub no site atual**. Portanto, GitHub permanece como fonte de verdade e histórico do código, mas a publicação na Hostinger será feita manualmente por pacote.

## 4. Fluxo oficial de versionamento e deploy

Fluxo definido para a V1:

```text
GitHub
  ↓
branch/revisão/commit aprovado
  ↓
geração do pacote de produção
  ↓
validação do conteúdo do pacote
  ↓
Hostinger hPanel / Gerenciador de Arquivos
  ↓
upload manual
  ↓
extração/cópia para public_html
  ↓
testes pós-deploy
```

### 4.1 Papel do GitHub

GitHub continua sendo usado para:

- código-fonte oficial;
- histórico de alterações;
- revisão;
- commits;
- rollback lógico;
- preparação da versão que será empacotada.

A Hostinger não é a fonte de verdade do código.

### 4.2 Papel do pacote de deploy

A implementação deve permitir gerar um pacote contendo **somente os arquivos necessários para produção**.

Estrutura conceitual do conteúdo do pacote:

```text
public_html/
├── .htaccess
├── feminino/
├── assets/
├── go/
└── error/
```

O pacote não deve exigir o upload do repositório inteiro nem incluir documentação, arquivos de desenvolvimento ou módulos não relacionados à landing.

### 4.3 Publicação manual

A publicação será feita no hPanel, preferencialmente pelo Gerenciador de Arquivos, por meio de upload e extração/cópia do pacote para `public_html` ou diretório público equivalente.

FTP pode ser usado como alternativa operacional se necessário.

Não há requisito de integração automática GitHub → Hostinger na V1.

## 5. URLs oficiais da V1

Landing feminina:

```text
https://mktdigitalofertas.com.br/feminino
```

Rota controlada para WhatsApp:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

A rota pública deve permanecer estável mesmo quando o grupo ou convite do WhatsApp mudar.

## 6. Arquitetura do redirect WhatsApp

Fluxo técnico:

```text
/feminino
    ↓
HTML/CSS/JS
    ↓
CTA WhatsApp
    ↓
/go/whatsapp/feminino
    ↓
PHP
    ↓
configuração centralizada do destino
    ↓
validação
    ↓
HTTP 302
    ↓
convite atual do grupo WhatsApp
```

O convite real do grupo não deve ser gravado diretamente no HTML ou JavaScript da landing enquanto for possível manter essa separação sem complexidade relevante.

O objetivo dessa separação não é tornar o convite secreto. O endereço final poderá ser observado pelo navegador durante o redirect. O objetivo é:

- centralizar o destino;
- evitar duplicação do convite;
- permitir troca do grupo sem editar a landing;
- manter anúncios, QR Codes, bio e URLs públicas estáveis;
- reduzir risco de links antigos permanecerem publicados.

Regra resumida:

> Centralizar o link, não tentar escondê-lo.

## 7. Configuração do convite

A V1 deve manter uma única fonte de configuração para o destino do nicho feminino.

A configuração pode ser implementada em PHP, preferencialmente sem expor o valor no HTML ou JavaScript entregue ao navegador.

A localização exata do arquivo/configuração deve seguir a solução mais simples suportada pelo ambiente Hostinger e pelo processo de pacote manual.

Não é requisito criar infraestrutura adicional apenas para proteger esse valor.

Ao gerar o pacote de deploy, a configuração necessária para produção deve estar claramente documentada. Se o arquivo de configuração não for versionado com o convite real, o processo deve indicar exatamente onde inserir o valor antes ou depois do upload.

## 8. Estrutura de arquivos de referência

Estrutura conceitual compatível com a hospedagem:

```text
public_html/
├── feminino/
│   └── index.html
├── assets/
│   ├── css/
│   ├── js/
│   ├── img/
│   └── qr/
├── go/
│   └── whatsapp/
│       └── feminino.php
├── error/
│   └── whatsapp-indisponivel.html
└── .htaccess

configuração do WhatsApp
└── fonte única utilizada pelo PHP
```

A estrutura final pode ser ajustada durante a implementação desde que preserve os contratos de URL, a fonte única de configuração e a possibilidade de gerar um pacote simples para upload manual.

## 9. QR Code no desktop

A versão desktop da landing deve poder exibir um QR Code como alternativa ao botão de WhatsApp.

O QR Code deve apontar para a URL controlada do projeto:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

O QR Code não deve apontar diretamente para `chat.whatsapp.com`.

Motivo:

```text
QR Code permanente
      ↓
/go/whatsapp/feminino
      ↓
destino configurável
      ↓
grupo atual
```

Assim, trocar o grupo ou o convite não exige gerar ou redistribuir um novo QR Code.

### 9.1 Comportamento por dispositivo

**Mobile**

Priorizar o CTA:

> Quero receber as ofertas no WhatsApp

**Desktop**

Pode apresentar simultaneamente:

- CTA de WhatsApp;
- QR Code para abrir a mesma rota controlada no celular.

O QR Code é um recurso complementar e não substitui o CTA principal.

## 10. UTM e QR Code

Os CTAs originados de uma landing acessada com UTMs devem preservar os parâmetros conforme o contrato V1.

O QR Code institucional fixo pode utilizar a rota limpa sem UTM:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Caso no futuro existam QR Codes específicos por campanha, eles poderão apontar para a mesma rota com UTMs próprias, sem alterar a arquitetura.

## 11. Estado atual do domínio

Estado informado em 2026-08-27:

- domínio: `mktdigitalofertas.com.br`;
- domínio operacional;
- página atual: página padrão/vazia da hospedagem;
- aplicação da landing ainda não implantada.

Esse estado permite que a primeira publicação da landing seja tratada como implantação inicial, sem necessidade de migração de uma aplicação existente do projeto.

## 12. Preparação antes do primeiro deploy

Antes da publicação manual:

1. confirmar que o SSL do domínio está ativo;
2. abrir `public_html` e registrar o conteúdo existente antes de substituir qualquer arquivo;
3. gerar o pacote de produção a partir de uma versão/commit aprovado no GitHub;
4. validar que o pacote contém somente os arquivos necessários à landing;
5. validar onde ficará a configuração centralizada do convite;
6. manter backup simples dos arquivos atuais da página padrão caso seja necessário rollback;
7. fazer upload do pacote no hPanel;
8. extrair/copiar os arquivos para `public_html`;
9. executar o checklist pós-deploy.

## 13. Regras do pacote de produção

O pacote deve:

- poder ser extraído diretamente ou copiado de forma simples para `public_html`;
- conter a estrutura necessária para `/feminino` e `/go/whatsapp/feminino`;
- incluir `.htaccess` quando necessário;
- incluir PHP, CSS, JS, imagens e QR Code necessários;
- não incluir `.git`;
- não incluir documentação do projeto;
- não incluir arquivos de teste/desenvolvimento desnecessários;
- não incluir outros módulos do repositório;
- possuir instruções curtas de configuração e publicação.

A geração do pacote deve ser reproduzível a partir do repositório.

## 14. Rollback operacional

Como o deploy é manual, o rollback da V1 deve ser simples:

1. manter o commit/tag ou referência da versão anterior no GitHub;
2. manter, quando aplicável, uma cópia do pacote anterior;
3. em caso de falha, reenviar o pacote anterior ou restaurar o backup dos arquivos substituídos;
4. testar novamente as URLs principais.

## 15. Critérios de aceite técnico

A arquitetura desta etapa será considerada implementada quando:

1. `https://mktdigitalofertas.com.br/feminino` carregar a landing;
2. HTML/CSS/JS forem servidos via HTTPS;
3. `/go/whatsapp/feminino` executar o fluxo PHP de redirect;
4. o redirect usar HTTP 302;
5. o convite não estiver hardcoded no HTML/JS da landing;
6. houver uma única fonte de configuração do destino;
7. trocar o destino não exigir alteração da landing;
8. o QR Code desktop apontar para `/go/whatsapp/feminino`;
9. o botão mobile e o QR Code desktop chegarem ao mesmo destino lógico;
10. o código publicado estiver versionado no GitHub;
11. existir um pacote de produção limpo e reproduzível;
12. o deploy puder ser executado manualmente pelo hPanel sem enviar o repositório inteiro;
13. existir checklist de publicação e pós-deploy.

## 16. Próxima etapa

A especificação técnica de implementação deve usar este fluxo de deploy manual como contrato operacional e exigir do Codex a criação de um pacote pronto para upload na Hostinger.