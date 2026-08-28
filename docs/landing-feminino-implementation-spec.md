# Spec TÃ©cnica de ImplementaÃ§Ã£o â€” Landing Ofertas Femininas V1

**Status:** Pronta para implementaÃ§Ã£o
**Data:** 2026-08-27
**Branch de definiÃ§Ã£o:** `docs/feminino-calcados-discovery`
**DomÃ­nio de produÃ§Ã£o:** `https://mktdigitalofertas.com.br`

## 1. Objetivo

Implementar a primeira landing pÃºblica do projeto **Ofertas Femininas**, usando as decisÃµes jÃ¡ consolidadas em:

- `docs/landing-v1-contract.md`;
- `docs/landing-feminino-sistema-visual.md`;
- `docs/landing-feminino-wireframe.md`;
- `docs/landing-feminino-arquitetura-hostinger.md`.

A implementaÃ§Ã£o nÃ£o deve reinterpretar estratÃ©gia, copy, identidade visual ou arquitetura jÃ¡ decididas.

## 2. Escopo da implementaÃ§Ã£o

A V1 deve entregar:

1. landing pÃºblica em `https://mktdigitalofertas.com.br/feminino`;
2. HTML/CSS/JS responsivo e mobile-first;
3. Hero e demais seÃ§Ãµes conforme wireframe aprovado;
4. CTA principal para WhatsApp;
5. preservaÃ§Ã£o dos parÃ¢metros UTM atÃ© a rota de saÃ­da;
6. rota controlada `https://mktdigitalofertas.com.br/go/whatsapp/feminino`;
7. redirect HTTP `302` via PHP;
8. configuraÃ§Ã£o Ãºnica do convite ativo do WhatsApp fora do HTML/JS;
9. QR Code na experiÃªncia desktop apontando para a rota controlada;
10. `.htaccess` para URLs limpas/rewrite, se necessÃ¡rio;
11. tratamento de erro controlado quando o destino WhatsApp nÃ£o estiver configurado ou for invÃ¡lido;
12. pacote de produÃ§Ã£o pronto para upload manual no hPanel da Hostinger.

## 3. Fora do escopo

NÃ£o implementar nesta V1:

- WordPress;
- Node.js;
- banco de dados;
- Supabase;
- GA4;
- Meta Pixel;
- Meta Conversion API;
- login;
- CMS;
- dashboard;
- roteamento entre mÃºltiplos grupos do mesmo nicho;
- mediÃ§Ã£o de entrada efetiva no grupo;
- armazenamento persistente das UTMs;
- geraÃ§Ã£o dinÃ¢mica de ofertas a partir de APIs;
- automaÃ§Ã£o de atualizaÃ§Ã£o dos cards de produto;
- testes A/B;
- integraÃ§Ã£o automÃ¡tica GitHub â†’ Hostinger.

## 4. Stack

Usar apenas:

- HTML5;
- CSS3;
- JavaScript vanilla quando necessÃ¡rio;
- PHP suportado pela Hostinger;
- `.htaccess` / `mod_rewrite` quando necessÃ¡rio;
- assets locais otimizados.

Evitar frameworks e dependÃªncias desnecessÃ¡rias.

## 5. Estrutura de arquivos esperada

Estrutura equivalente Ã  abaixo:

```text
public_html/
â”œâ”€â”€ .htaccess
â”œâ”€â”€ feminino/
â”‚   â””â”€â”€ index.html
â”œâ”€â”€ assets/
â”‚   â”œâ”€â”€ css/
â”‚   â”‚   â””â”€â”€ feminino.css
â”‚   â”œâ”€â”€ js/
â”‚   â”‚   â””â”€â”€ feminino.js
â”‚   â”œâ”€â”€ img/
â”‚   â””â”€â”€ qr/
â”œâ”€â”€ go/
â”‚   â””â”€â”€ whatsapp/
â”‚       â””â”€â”€ feminino.php
â””â”€â”€ error/
    â””â”€â”€ whatsapp-indisponivel.html
```

A configuraÃ§Ã£o do convite nÃ£o deve ficar no HTML ou JavaScript pÃºblico.

O requisito obrigatÃ³rio Ã© **centralizaÃ§Ã£o do destino**, nÃ£o sigilo absoluto. Se for simples no ambiente Hostinger, usar arquivo PHP dedicado para configuraÃ§Ã£o. NÃ£o criar infraestrutura adicional apenas para esconder o convite.

## 6. URLs oficiais

### Landing

```text
GET https://mktdigitalofertas.com.br/feminino
```

Aceita opcionalmente:

```text
utm_source
utm_medium
utm_campaign
utm_content
utm_term
```

### Redirect WhatsApp

```text
GET https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Resposta normal:

```text
HTTP 302
Location: <CONVITE_WHATSAPP_CONFIGURADO>
```

## 7. Comportamento de UTM

Ao carregar `/feminino`, preservar nos CTAs apenas os parÃ¢metros UTM suportados presentes na URL.

Exemplo:

```text
Entrada:
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01

CTA:
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
```

Regras:

- UTMs sÃ£o opcionais;
- parÃ¢metros ausentes nÃ£o devem ser inventados;
- valores desconhecidos devem ser preservados como texto;
- ausÃªncia de UTM nÃ£o pode quebrar a landing;
- nÃ£o adicionar UTM ao link final `chat.whatsapp.com`;
- nÃ£o persistir UTM em banco, cookie ou localStorage.

## 8. Redirect WhatsApp

O PHP deve:

1. carregar a configuraÃ§Ã£o centralizada do nicho feminino;
2. verificar que existe;
3. verificar que nÃ£o estÃ¡ vazia;
4. verificar que Ã© URL HTTPS vÃ¡lida;
5. verificar formato/domÃ­nio aceito para convite WhatsApp;
6. responder HTTP `302` com `Location` quando vÃ¡lido;
7. interromper a execuÃ§Ã£o apÃ³s o redirect.

NÃ£o usar `301`.

NÃ£o colocar o convite diretamente:

- no HTML;
- em JavaScript;
- no QR Code;
- em anÃºncios;
- em mÃºltiplos arquivos de configuraÃ§Ã£o.

## 9. Falha controlada

Se o convite estiver ausente ou invÃ¡lido:

- nÃ£o redirecionar;
- nÃ£o usar fallback silencioso;
- nÃ£o redirecionar para outro nicho;
- nÃ£o expor paths, variÃ¡veis, stack trace ou detalhes internos;
- apresentar pÃ¡gina amigÃ¡vel de indisponibilidade.

Copy-base:

> O acesso ao grupo estÃ¡ temporariamente indisponÃ­vel.
>
> Tente novamente em alguns minutos.

## 10. QR Code

Na versÃ£o desktop, exibir QR Code como mecanismo complementar.

O QR Code deve codificar:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Nunca codificar diretamente `chat.whatsapp.com`.

- desktop: botÃ£o + QR Code podem coexistir;
- mobile: botÃ£o Ã© prioritÃ¡rio e QR Code pode ser ocultado;
- QR Code institucional pode usar a rota sem UTM.

## 11. Wireframe obrigatÃ³rio

Seguir `docs/landing-feminino-wireframe.md`.

Ordem:

1. Hero;
2. faixa de confianÃ§a;
3. macrogrupos;
4. Como funciona;
5. prova de curadoria / exemplos reais;
6. Vitrine Shopee;
7. reforÃ§o de urgÃªncia real;
8. CTA final;
9. rodapÃ©.

## 12. Copy obrigatÃ³ria/base

Usar os textos consolidados em `docs/landing-v1-contract.md`.

### Hero

**TÃ­tulo**

> Ofertas e cupons para mulheres, nÃ£o perca tempo procurando

**SubtÃ­tulo**

> Receba no WhatsApp Ã³timos produtos de beleza, moda, calÃ§ados, bolsas, cabelos e skincare.

**Gancho**

> Os preÃ§os mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

### ConfianÃ§a

> ðŸ’Ž Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÃVEIS

### OperaÃ§Ã£o pÃºblica

> ðŸŒ™ Seu descanso Ã© respeitado. As mensagens param Ã  noite e sÃ³ voltam pela manhÃ£. O grupo fica em silÃªncio aproximadamente entre 21h10 e 8h.

> ðŸ”• SÃ³ administradores enviam mensagens

NÃ£o introduzir quantidade fixa de mensagens por dia ou horÃ¡rios individuais de triggers.

## 13. Macrogrupos

Exibir exatamente:

- ðŸ’„ Beleza
- ðŸ‘— Moda
- ðŸ‘  CalÃ§ados
- ðŸ‘œ Bolsas e acessÃ³rios
- ðŸ’‡â€â™€ï¸ Cabelos
- ðŸ§´ Skincare

NÃ£o alterar a taxonomia interna do projeto.

## 14. Sistema visual

Seguir `docs/landing-feminino-sistema-visual.md`.

Diretrizes essenciais:

- identidade Ofertas Femininas dominante;
- fundo creme/rosado claro;
- coral/terracota nos CTAs;
- vinho/vermelho escuro nos tÃ­tulos;
- rosa/pÃªssego nos blocos secundÃ¡rios;
- serifada elegante para tÃ­tulos;
- sans-serif legÃ­vel para textos;
- banner institucional das quatro mulheres como referÃªncia do Hero;
- peÃ§a de oferta como referÃªncia de cards e linguagem comercial;
- Shopee e Amazon visualmente subordinadas Ã  marca.

## 15. Assets

ReferÃªncias oficiais:

1. banner institucional Ofertas Femininas com quatro mulheres;
2. peÃ§a visual de oferta/produto fornecida na definiÃ§Ã£o visual.

Usar assets existentes no repositÃ³rio se jÃ¡ existirem. Caso nÃ£o existam, deixar caminhos/estrutura claramente preparados e documentar onde inserir os arquivos. NÃ£o inventar arquivos como se jÃ¡ existissem.

Otimizar imagens para web quando apropriado.

## 16. Cards de prova de curadoria

Criar estrutura para aproximadamente 3 a 4 cards.

Cada card deve suportar:

- imagem;
- nome;
- marketplace;
- preÃ§o/oferta quando real;
- cupom quando real;
- CTA secundÃ¡rio.

CTAs possÃ­veis:

- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calÃ§ados`;
- `Ver nossa seleÃ§Ã£o na Shopee`.

NÃ£o inventar preÃ§o, estoque, desconto ou validade. Se nÃ£o houver exemplos reais definidos, usar placeholders claramente identificados no cÃ³digo e facilmente substituÃ­veis.

## 17. Vitrine Shopee

A Vitrine Shopee Ã© secundÃ¡ria.

CTA-base:

> Ver nossa seleÃ§Ã£o na Shopee

Hierarquia visual:

```text
WhatsApp > Vitrine Shopee > oferta/cupom individual
```

## 18. Responsividade

### Mobile

- CTA principal aparece cedo;
- Hero nÃ£o Ã© dominado pela ilustraÃ§Ã£o;
- seÃ§Ãµes empilhadas;
- macrogrupos compactos;
- cards responsivos;
- QR Code pode ser ocultado;
- botÃµes com Ã¡rea de toque adequada.

### Desktop

- Hero em duas colunas quando adequado;
- copy Ã  esquerda e asset institucional Ã  direita;
- botÃ£o WhatsApp + QR Code podem coexistir;
- cards em grid responsivo.

## 19. CTA fixo mobile

CTA fixo inferior Ã© **opcional**.

Se implementado:

- nÃ£o pode ser invasivo;
- nÃ£o pode cobrir conteÃºdo;
- deve preservar UTMs;
- deve ser fÃ¡cil de desativar.

## 20. `.htaccess` e URLs limpas

Configurar apenas o necessÃ¡rio.

- evitar loops;
- nÃ£o transformar o redirect WhatsApp em permanente;
- manter `.htaccess` mÃ­nimo se a estrutura fÃ­sica de diretÃ³rios jÃ¡ resolver as URLs.

## 21. SEO e acessibilidade mÃ­nimos

Incluir:

- `<title>`;
- meta description;
- viewport;
- `lang="pt-BR"`;
- headings semÃ¢nticos;
- `alt` em imagens relevantes;
- foco de teclado visÃ­vel;
- contraste suficiente;
- botÃµes/links semanticamente corretos;
- alternativa textual ao QR Code.

## 22. Performance

- sem bibliotecas grandes desnecessÃ¡rias;
- imagens otimizadas;
- JS mÃ­nimo;
- sem autoplay de vÃ­deo;
- poucas fontes;
- evitar efeitos pesados;
- priorizar carregamento mÃ³vel rÃ¡pido.

## 23. SeguranÃ§a e robustez

- validar qualquer valor usado pelo PHP;
- nÃ£o construir `Location` com entrada arbitrÃ¡ria do visitante;
- destino vem somente da configuraÃ§Ã£o controlada;
- nÃ£o expor erros internos;
- nÃ£o ativar display de erros PHP em produÃ§Ã£o;
- UTM Ã© apenas dado textual de navegaÃ§Ã£o.

## 24. Versionamento e deploy manual na Hostinger

GitHub permanece como fonte de verdade do cÃ³digo, mas **nÃ£o existe integraÃ§Ã£o GitHub â†’ Hostinger para esta implantaÃ§Ã£o**.

Fluxo oficial:

```text
GitHub
  â†“
branch/revisÃ£o/commit aprovado
  â†“
gerar pacote de produÃ§Ã£o
  â†“
validar pacote
  â†“
Hostinger hPanel / Gerenciador de Arquivos
  â†“
upload manual
  â†“
extrair/copiar para public_html
  â†“
testes pÃ³s-deploy
```

FTP pode ser usado como alternativa manual se necessÃ¡rio.

## 25. Pacote de produÃ§Ã£o obrigatÃ³rio

A implementaÃ§Ã£o deve gerar ou deixar pronta uma forma simples e reproduzÃ­vel de gerar um pacote contendo somente o necessÃ¡rio para produÃ§Ã£o.

ConteÃºdo esperado:

```text
deploy/
â””â”€â”€ public_html/
    â”œâ”€â”€ .htaccess
    â”œâ”€â”€ feminino/
    â”œâ”€â”€ assets/
    â”œâ”€â”€ go/
    â””â”€â”€ error/
```

O nome exato da pasta de preparaÃ§Ã£o pode variar, mas o conteÃºdo final deve poder ser copiado de forma simples para `public_html`.

O pacote nÃ£o deve incluir:

- `.git`;
- documentaÃ§Ã£o;
- arquivos de desenvolvimento nÃ£o necessÃ¡rios;
- outros mÃ³dulos do projeto;
- segredos desnecessÃ¡rios;
- cÃ³digo de n8n, catÃ¡logo, Supabase ou automaÃ§Ãµes nÃ£o relacionadas.

Se houver arquivo de configuraÃ§Ã£o do convite que precise ser ajustado manualmente, documentar exatamente:

- caminho;
- formato;
- valor esperado;
- momento em que deve ser configurado.

## 26. Estado atual do domÃ­nio

`https://mktdigitalofertas.com.br/` estÃ¡ operacional e apresenta apenas a pÃ¡gina padrÃ£o da hospedagem.

Antes do primeiro upload:

- verificar o conteÃºdo atual de `public_html`;
- manter backup simples dos arquivos existentes antes de substituir;
- nÃ£o apagar arquivos desconhecidos sem inspeÃ§Ã£o.

## 27. Checklist de deploy manual

Antes do upload:

1. confirmar commit/versionamento da versÃ£o a publicar;
2. gerar pacote de produÃ§Ã£o;
3. revisar o conteÃºdo do pacote;
4. confirmar configuraÃ§Ã£o do convite;
5. confirmar que `.htaccess` estÃ¡ incluÃ­do quando necessÃ¡rio;
6. confirmar que assets necessÃ¡rios estÃ£o presentes;
7. criar backup do conteÃºdo atual de `public_html`.

PublicaÃ§Ã£o:

8. subir o pacote pelo hPanel;
9. extrair/copiar o conteÃºdo para `public_html`;
10. conferir permissÃµes/estrutura se necessÃ¡rio;
11. nÃ£o executar mudanÃ§as fora do diretÃ³rio da landing sem necessidade.

PÃ³s-deploy:

12. abrir `/feminino`;
13. testar CTA;
14. testar redirect `302`;
15. testar QR Code;
16. testar mobile e desktop;
17. testar URL com UTM;
18. verificar HTTPS;
19. confirmar que nÃ£o hÃ¡ erros visÃ­veis de PHP ou assets quebrados.

## 28. Testes obrigatÃ³rios

### Landing

1. `/feminino` sem query string;
2. `/feminino` com UTMs completas;
3. UTMs parciais;
4. mobile;
5. desktop;
6. imagens/fontes;
7. CTAs.

### UTM

8. CTA preserva UTMs atÃ© `/go/whatsapp/feminino`;
9. ausÃªncia de UTM nÃ£o cria parÃ¢metros vazios desnecessÃ¡rios.

### Redirect

10. HTTP `302`;
11. `Location` aponta para grupo configurado;
12. trocar configuraÃ§Ã£o muda destino sem editar landing;
13. configuraÃ§Ã£o ausente;
14. configuraÃ§Ã£o invÃ¡lida;
15. ausÃªncia de fallback silencioso.

### QR Code

16. escanear em celular real;
17. confirmar rota controlada;
18. confirmar independÃªncia do convite real.

### Visual

19. coerÃªncia com assets Ofertas Femininas;
20. WhatsApp Ã© CTA dominante;
21. Shopee/ofertas individuais sÃ£o secundÃ¡rios;
22. nÃ£o hÃ¡ promessa de volume diÃ¡rio fixo ou horÃ¡rios individuais de triggers.

### Pacote

23. pacote contÃ©m somente arquivos de produÃ§Ã£o necessÃ¡rios;
24. pacote pode ser copiado para `public_html` sem depender do repositÃ³rio inteiro;
25. instruÃ§Ãµes de configuraÃ§Ã£o/publicaÃ§Ã£o estÃ£o claras.

## 29. CritÃ©rios de aceite

A implementaÃ§Ã£o estÃ¡ pronta quando:

1. `/feminino` carrega corretamente;
2. layout segue o wireframe;
3. identidade segue o sistema visual;
4. copy-base estÃ¡ correta;
5. funciona em mobile e desktop;
6. CTAs preservam UTMs;
7. `/go/whatsapp/feminino` retorna `302` para destino configurado;
8. convite real nÃ£o estÃ¡ no HTML/JS nem no QR Code;
9. trocar convite exige alterar somente a configuraÃ§Ã£o centralizada;
10. erro de configuraÃ§Ã£o gera falha controlada;
11. QR Code desktop funciona;
12. nÃ£o hÃ¡ dependÃªncia de banco, WordPress, Node.js ou serviÃ§os externos obrigatÃ³rios;
13. existe pacote de produÃ§Ã£o pronto para upload manual;
14. existe checklist de upload e pÃ³s-deploy;
15. todos os testes relevantes passam.

## 30. InstruÃ§Ã£o para o Codex

Implementar esta spec de forma incremental e conservadora.

### Regras

- Ler integralmente os quatro documentos referenciados na seÃ§Ã£o 1.
- NÃ£o alterar regras de negÃ³cio, copy aprovada, wireframe ou identidade sem solicitaÃ§Ã£o explÃ­cita.
- NÃ£o adicionar frameworks ou infraestrutura fora do escopo.
- NÃ£o modificar workflows, automaÃ§Ãµes, catÃ¡logo, n8n, Supabase ou outras Ã¡reas do projeto.
- Trabalhar somente nos arquivos necessÃ¡rios para a landing e redirect.
- Manter convite centralizado e fora do HTML/JS.
- Preservar UTM de forma simples e testÃ¡vel.
- Gerar QR Code a partir da rota estÃ¡vel, nunca do convite real.
- Preparar pacote de produÃ§Ã£o para upload manual na Hostinger.
- **NÃ£o fazer deploy real.**
- **NÃ£o configurar integraÃ§Ã£o Git da Hostinger.**
- NÃ£o sobrescrever nem manipular o servidor Hostinger.

### Resultado esperado do Codex

Ao finalizar, apresentar:

1. arquivos criados/alterados;
2. arquitetura final;
3. como configurar e trocar o convite do WhatsApp;
4. como testar localmente quando possÃ­vel;
5. caminho/estrutura do pacote de produÃ§Ã£o;
6. como gerar o pacote novamente;
7. checklist de upload manual no hPanel;
8. checklist pÃ³s-deploy;
9. qualquer pendÃªncia de assets ou configuraÃ§Ã£o externa.
