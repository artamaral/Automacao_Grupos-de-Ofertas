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
- deploy pela integração Git da Hostinger, quando a opção estiver disponível no hPanel do site.

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

A integração Git deve ser confirmada no hPanel depois que `mktdigitalofertas.com.br` estiver corretamente vinculado ao site/plano. O caminho informado pela Hostinger é:

```text
Websites → Gerenciar/Dashboard → Advanced → Git
```

## 4. Deploy preferencial

O método preferencial de deploy da V1 será GitHub → Hostinger.

Fluxo:

```text
GitHub
  ↓
branch de produção
  ↓
Hostinger / Advanced / Git
  ↓
Deploy
  ↓
public_html
  ↓
HTML + CSS + JS + PHP + .htaccess
```

A integração da Hostinger permite, quando disponível no site/plano:

- conectar uma conta GitHub;
- selecionar o repositório;
- selecionar uma branch;
- definir o diretório raiz do deploy;
- publicar os arquivos do projeto.

A branch atual `docs/feminino-calcados-discovery` é uma branch de definição/documentação e não deve ser tratada automaticamente como branch permanente de produção. A estratégia final de branch de deploy deve ser definida durante a implementação.

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

A localização exata do arquivo/configuração deve seguir a solução mais simples suportada pelo ambiente Hostinger no momento da implantação.

Não é requisito criar uma infraestrutura adicional apenas para proteger esse valor.

## 8. Estrutura de arquivos de referência

Estrutura conceitual compatível com a hospedagem:

```text
public_html/
├── feminino/
│   └── index.html
├── assets/
│   ├── css/
│   ├── js/
│   └── img/
├── go/
│   └── whatsapp/
│       └── feminino.php
└── .htaccess

configuração do WhatsApp
└── fonte única utilizada pelo PHP
```

A estrutura final pode ser ajustada durante a implementação desde que preserve os contratos de URL e a fonte única de configuração.

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

## 12. Pendências antes do primeiro deploy

Antes da publicação, confirmar no hPanel:

1. que `mktdigitalofertas.com.br` está vinculado ao site/plano correto;
2. que `Advanced → Git` aparece para esse site;
3. que o repositório GitHub pode ser conectado;
4. que uma branch específica pode ser selecionada;
5. qual diretório raiz será usado no deploy;
6. que o deploy chega ao `public_html` ou ao diretório público equivalente;
7. que o SSL do domínio está ativo.

Caso Git não esteja disponível no site após o vínculo correto, FTP/Gerenciador de Arquivos são fallback operacional, não a primeira opção.

## 13. Critérios de aceite técnico

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
10. o código implantado estiver versionado no GitHub;
11. o método preferencial de deploy for Git, quando a opção estiver habilitada para o site.

## 14. Próxima etapa

Com arquitetura, wireframe, copy e sistema visual definidos, o próximo passo é elaborar a **especificação técnica de implementação**, definindo os arquivos, responsabilidades, regras de rewrite, comportamento do PHP, geração do QR Code, assets e testes necessários antes de iniciar o código.
