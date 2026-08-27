# Spec Técnica de Implementação — Landing Ofertas Femininas V1

**Status:** Pronta para implementação  
**Data:** 2026-08-27  
**Branch de definição:** `docs/feminino-calcados-discovery`  
**Domínio de produção:** `https://mktdigitalofertas.com.br`

## 1. Objetivo

Implementar a primeira landing pública do projeto **Ofertas Femininas**, usando as decisões já consolidadas em:

- `docs/landing-v1-contract.md`;
- `docs/landing-feminino-sistema-visual.md`;
- `docs/landing-feminino-wireframe.md`;
- `docs/landing-feminino-arquitetura-hostinger.md`.

A implementação não deve reinterpretar a estratégia, copy, identidade visual ou arquitetura já decididas. Quando houver conflito entre implementação sugerida e os documentos acima, prevalecem os contratos/documentos de decisão.

## 2. Escopo da implementação

A V1 deve entregar:

1. landing pública em `https://mktdigitalofertas.com.br/feminino`;
2. HTML/CSS/JS responsivo e mobile-first;
3. Hero e demais seções conforme wireframe aprovado;
4. CTA principal para WhatsApp;
5. preservação dos parâmetros UTM até a rota de saída;
6. rota controlada `https://mktdigitalofertas.com.br/go/whatsapp/feminino`;
7. redirect HTTP `302` via PHP;
8. configuração única do convite ativo do WhatsApp fora do HTML/JS;
9. QR Code na experiência desktop apontando para a rota controlada;
10. `.htaccess` para URLs limpas/rewrite, se necessário;
11. estrutura pronta para deploy via Git na Hostinger;
12. tratamento de erro controlado quando o destino WhatsApp não estiver configurado ou for inválido.

## 3. Fora do escopo

Não implementar nesta V1:

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
- roteamento entre múltiplos grupos do mesmo nicho;
- medição de entrada efetiva no grupo;
- armazenamento persistente das UTMs;
- geração dinâmica de ofertas a partir de APIs;
- automação de atualização dos cards de produto;
- testes A/B.

## 4. Stack

Usar apenas:

- HTML5;
- CSS3;
- JavaScript vanilla quando necessário;
- PHP suportado pela Hostinger;
- `.htaccess` / `mod_rewrite` quando necessário para URLs limpas;
- assets locais otimizados.

Evitar frameworks e dependências desnecessárias.

## 5. Estrutura de arquivos esperada

A implementação pode usar estrutura equivalente à abaixo:

```text
public_html/
├── .htaccess
├── feminino/
│   └── index.html
├── assets/
│   ├── css/
│   │   └── feminino.css
│   ├── js/
│   │   └── feminino.js
│   ├── img/
│   │   ├── ofertas-femininas-hero.*
│   │   ├── oferta-referencia.*
│   │   └── ...
│   └── qr/
│       └── feminino-whatsapp.*
├── go/
│   └── whatsapp/
│       └── feminino.php
└── error/
    └── whatsapp-indisponivel.html
```

A configuração do convite não deve ficar no HTML ou JavaScript público.

A configuração pode ser mantida em PHP de forma centralizada, preferencialmente fora do diretório público quando o ambiente Hostinger permitir isso sem aumentar significativamente a complexidade.

Exemplo conceitual:

```text
private/
└── whatsapp-config.php
```

Se manter a configuração fora de `public_html` complicar o deploy Git do plano atual, pode ser usada uma configuração PHP não exposta diretamente como texto pelo servidor. O requisito obrigatório é **centralização do destino**, não sigilo absoluto.

## 6. URLs oficiais

### 6.1 Landing

```text
GET https://mktdigitalofertas.com.br/feminino
```

Deve aceitar opcionalmente:

```text
utm_source
utm_medium
utm_campaign
utm_content
utm_term
```

### 6.2 Redirect WhatsApp

```text
GET https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Também deve aceitar os mesmos parâmetros UTM preservados da landing.

Resposta normal:

```text
HTTP 302
Location: <CONVITE_WHATSAPP_CONFIGURADO>
```

## 7. Comportamento de UTM

Ao carregar `/feminino`, o JavaScript deve ler apenas os parâmetros UTM suportados presentes na URL e preservá-los no destino dos CTAs do WhatsApp.

Exemplo:

```text
Entrada:
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01

CTA gerado:
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
```

Regras:

- UTMs são opcionais;
- parâmetros ausentes não devem ser inventados;
- valores desconhecidos devem ser preservados como texto;
- a landing não deve falhar se nenhuma UTM estiver presente;
- não é necessário acrescentar UTM ao link final `chat.whatsapp.com`;
- não armazenar UTM em banco, cookie ou localStorage na V1.

## 8. Redirect WhatsApp

O arquivo PHP responsável pela rota deve:

1. carregar a configuração centralizada do nicho feminino;
2. verificar que o valor existe;
3. verificar que não está vazio;
4. verificar que é uma URL HTTPS válida;
5. verificar que corresponde a um formato/domínio de convite WhatsApp aceito pela implementação;
6. responder com HTTP `302` e header `Location` quando válido;
7. interromper a execução após o redirect.

Não usar redirect `301`.

Não colocar o convite diretamente:

- no HTML;
- em JavaScript;
- no QR Code;
- em anúncios;
- em múltiplos arquivos de configuração.

## 9. Falha controlada do redirect

Se o convite estiver ausente ou inválido:

- não redirecionar;
- não usar convite antigo como fallback;
- não redirecionar para outro nicho;
- não mostrar path de arquivo, variável, stack trace ou detalhes internos;
- responder com uma página simples e amigável informando indisponibilidade temporária.

Copy-base sugerida:

> O acesso ao grupo está temporariamente indisponível.
>
> Tente novamente em alguns minutos.

A página de erro deve manter linguagem visual mínima coerente com Ofertas Femininas.

## 10. QR Code

### 10.1 Regra

Na versão desktop, exibir QR Code como mecanismo adicional de entrada no grupo.

O QR Code deve codificar:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Não codificar diretamente o convite `chat.whatsapp.com`.

### 10.2 UTM e QR Code

Para a V1, o QR Code institucional pode apontar para a rota estável sem UTM.

Se futuramente houver necessidade de atribuição específica do QR Code, poderá ser criada uma URL com UTM própria sem alterar a arquitetura.

### 10.3 Responsividade

- desktop: botão + QR Code podem coexistir;
- mobile: o botão é prioritário e o QR Code pode ser ocultado para evitar redundância;
- o QR Code não deve competir visualmente com o CTA principal.

## 11. Wireframe obrigatório

A ordem principal da landing deve seguir:

1. Hero;
2. faixa de confiança;
3. macrogrupos;
4. Como funciona;
5. prova de curadoria / exemplos reais;
6. Vitrine Shopee;
7. reforço de urgência real;
8. CTA final;
9. rodapé.

O documento `docs/landing-feminino-wireframe.md` é a referência oficial para disposição desktop/mobile.

## 12. Copy obrigatória/base

Usar como base os textos consolidados em `docs/landing-v1-contract.md`.

### Hero

**Título**

> Ofertas e cupons para mulheres, não perca tempo procurando

**Subtítulo**

> Receba no WhatsApp ótimos produtos de beleza, moda, calçados, bolsas, cabelos e skincare.

**Gancho**

> Os preços mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

### Confiança

> 💎 Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÁVEIS

### Operação pública

> 🌙 Seu descanso é respeitado. As mensagens param à noite e só voltam pela manhã. O grupo fica em silêncio aproximadamente entre 21h10 e 8h.

> 🔕 Só administradores enviam mensagens

A implementação não deve introduzir quantidade fixa de mensagens por dia ou grade de horários de triggers.

## 13. Macrogrupos

Exibir exatamente:

- 💄 Beleza
- 👗 Moda
- 👠 Calçados
- 👜 Bolsas e acessórios
- 💇‍♀️ Cabelos
- 🧴 Skincare

Esses nomes são camada de apresentação e não devem ser usados para alterar a taxonomia interna do projeto.

## 14. Sistema visual

Usar `docs/landing-feminino-sistema-visual.md` como referência oficial.

Diretrizes essenciais:

- identidade Ofertas Femininas deve ser dominante;
- fundo creme/rosado claro;
- coral/terracota nos CTAs;
- vinho/vermelho escuro nos títulos;
- rosa/pêssego em blocos secundários;
- serifada elegante para títulos;
- sans-serif legível para textos e botões;
- banner institucional das quatro mulheres como referência do Hero;
- peça de oferta existente como referência de cards e linguagem comercial;
- Shopee e Amazon visualmente subordinadas à marca Ofertas Femininas.

## 15. Assets

Os dois assets fornecidos na definição visual devem ser tratados como referência oficial:

1. banner institucional Ofertas Femininas com quatro mulheres;
2. peça visual de oferta/produto usada como referência de cor, tipografia, preço, bordas, fundo e composição.

Durante a implementação, copiar/adicionar ao repositório apenas os arquivos de imagem necessários e permitidos, usando nomes descritivos.

Não modificar os assets originais sem necessidade.

Otimizar para web quando apropriado, mantendo qualidade visual suficiente.

## 16. Cards de prova de curadoria

A V1 pode conter aproximadamente 3 a 4 ofertas reais.

Cada card deve suportar:

- imagem;
- nome do produto;
- marketplace;
- preço/oferta quando atual;
- cupom quando aplicável;
- CTA secundário.

CTAs possíveis:

- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calçados`;
- `Ver nossa seleção na Shopee`.

Não inventar preço, estoque, desconto ou validade.

Se no momento da implementação ainda não houver exemplos reais definidos, construir a estrutura dos cards de forma que os dados possam ser substituídos facilmente sem alterar o layout.

## 17. Vitrine Shopee

A Vitrine Shopee é secundária.

CTA-base:

> Ver nossa seleção na Shopee

Ela não deve ter peso visual maior que o CTA do WhatsApp.

## 18. Responsividade

### Mobile

Prioridades:

- CTA principal aparecer cedo;
- Hero não ser dominado pela ilustração;
- seções empilhadas;
- macrogrupos em grid/chips compactos;
- cards de oferta empilhados ou em carrossel simples;
- QR Code pode ser ocultado;
- botões com área de toque confortável.

### Desktop

- Hero pode usar duas colunas;
- copy à esquerda e asset institucional à direita;
- botão WhatsApp + QR Code podem coexistir;
- cards podem usar grid de 3 ou 4 colunas conforme largura disponível.

## 19. CTA fixo mobile

Um CTA fixo discreto no rodapé da viewport mobile é **opcional**.

Não é requisito para aceite da primeira implementação.

Caso seja implementado:

- deve aparecer somente após o usuário deixar a região inicial do Hero ou em comportamento equivalente não invasivo;
- não pode cobrir conteúdo importante;
- deve apontar para a mesma rota controlada com UTMs preservadas;
- deve ser fácil de remover/desativar.

## 20. `.htaccess` e URLs limpas

Configurar apenas o necessário para garantir que as URLs públicas definidas funcionem.

Não criar regras genéricas ou complexas sem necessidade.

A implementação deve evitar loops de redirect e não deve transformar o `302` de WhatsApp em redirect permanente.

Se a estrutura física de diretórios já permitir `/feminino` e `/go/whatsapp/feminino` sem rewrite adicional, manter `.htaccess` mínimo.

## 21. SEO mínimo

Mesmo sendo landing de aquisição, incluir:

- `<title>` coerente com Ofertas Femininas;
- `meta description` curta;
- `viewport` correto;
- `lang="pt-BR"`;
- headings em hierarquia semântica;
- `alt` nas imagens relevantes;
- favicon caso exista asset apropriado.

Não implementar estratégia SEO avançada nesta V1.

## 22. Acessibilidade mínima

- contraste suficiente;
- foco de teclado visível;
- botões/links semanticamente corretos;
- QR Code acompanhado de alternativa textual/botão;
- não depender apenas de cor para indicar ação;
- imagens decorativas com tratamento adequado;
- respeitar `prefers-reduced-motion` caso animações sejam introduzidas.

## 23. Performance

A landing deve ser leve.

Regras:

- não adicionar bibliotecas grandes para funções simples;
- otimizar imagens;
- evitar autoplay de vídeo;
- evitar fontes em excesso;
- adiar JavaScript não crítico;
- evitar efeitos pesados;
- garantir carregamento aceitável em conexão móvel.

## 24. Segurança e robustez

- escapar/validar qualquer valor usado pelo PHP;
- não construir header `Location` com entrada arbitrária do visitante;
- o destino deve vir somente da configuração controlada;
- não expor arquivos internos por erro;
- não ativar display de erros PHP em produção;
- não executar código baseado em UTM;
- UTM é somente dado textual de navegação.

## 25. Deploy Git/Hostinger

Método preferencial:

```text
GitHub
  ↓
branch de deploy/produção definida no momento da implantação
  ↓
Hostinger hPanel → Advanced → Git
  ↓
Deploy
  ↓
site publicado
```

A branch `docs/feminino-calcados-discovery` é a branch atual de definição e documentação. Ela não deve ser assumida automaticamente como branch permanente de produção.

Antes do primeiro deploy, confirmar no hPanel:

1. domínio `mktdigitalofertas.com.br` vinculado ao site/plano correto;
2. opção `Advanced → Git` disponível;
3. repositório conectado;
4. branch de deploy escolhida explicitamente;
5. diretório raiz de deploy configurado corretamente;
6. HTTPS/SSL ativo.

Gerenciador de Arquivos e FTP são fallback operacional, não método preferencial.

## 26. Estado atual do domínio

No momento desta spec, `https://mktdigitalofertas.com.br/` está operacional e apresenta apenas a página padrão da hospedagem, sem aplicação de produção relevante a preservar.

A implantação deve ainda evitar apagar arquivos desconhecidos sem antes verificar o conteúdo de `public_html` durante o deploy inicial.

## 27. Testes obrigatórios antes da publicação

### Landing

1. abrir `/feminino` sem query string;
2. abrir `/feminino` com UTMs completas;
3. abrir com UTMs parciais;
4. validar mobile;
5. validar desktop;
6. validar imagens e fontes;
7. validar todos os CTAs.

### UTM

8. clicar no CTA com UTMs e confirmar que elas chegam à URL `/go/whatsapp/feminino`;
9. confirmar que ausência de UTM não cria parâmetros vazios desnecessários.

### Redirect

10. confirmar HTTP `302`;
11. confirmar `Location` apontando para o grupo configurado;
12. confirmar que mudar a configuração muda o destino sem editar a landing;
13. testar configuração ausente;
14. testar configuração inválida;
15. confirmar ausência de fallback silencioso.

### QR Code

16. escanear em um celular real;
17. confirmar que abre a rota controlada;
18. confirmar que continua independente do convite real do WhatsApp.

### Visual

19. validar coerência com os assets Ofertas Femininas;
20. confirmar que WhatsApp é o CTA dominante;
21. confirmar que Shopee/ofertas individuais são secundários;
22. confirmar que não há promessa de volume diário fixo ou horários individuais de triggers.

## 28. Critérios de aceite

A implementação está pronta quando:

1. `https://mktdigitalofertas.com.br/feminino` carrega corretamente;
2. layout segue o wireframe aprovado;
3. identidade segue o sistema visual aprovado;
4. copy-base definida aparece corretamente;
5. funciona em mobile e desktop;
6. CTAs preservam UTMs;
7. `/go/whatsapp/feminino` retorna `302` para o destino configurado;
8. convite real não está no HTML/JS nem no QR Code;
9. trocar o convite exige alterar somente a configuração centralizada;
10. erro de configuração gera falha controlada;
11. QR Code desktop funciona;
12. página não exige banco, WordPress, Node.js ou serviços externos para funcionar;
13. deploy pode ser realizado via Git na Hostinger após configuração do hPanel;
14. todos os testes obrigatórios relevantes passam.

## 29. Instrução para o Codex

Implementar esta spec de forma incremental e conservadora.

### Regras para implementação

- Ler antes os quatro documentos referenciados na seção 1.
- Não alterar regras de negócio, copy aprovada, wireframe ou identidade sem solicitação explícita.
- Não adicionar frameworks ou infraestrutura fora do escopo.
- Não modificar workflows, automações, seleção de ofertas, catálogo, n8n, Supabase ou demais partes do projeto não relacionadas à landing.
- Trabalhar somente nos arquivos necessários para a landing e seu redirect.
- Manter o convite do WhatsApp centralizado e fora do HTML/JS.
- Implementar preservação de UTM de forma simples e testável.
- Gerar o QR Code a partir da rota estável do projeto, nunca do convite real.
- Criar testes ou roteiro de validação suficiente para comprovar cada critério de aceite.
- Antes de qualquer deploy real, mostrar os arquivos alterados e o plano de implantação.
- Não sobrescrever o conteúdo do servidor Hostinger sem verificar o diretório de destino.

### Resultado esperado do Codex

Ao finalizar, apresentar:

1. resumo dos arquivos criados/alterados;
2. estrutura final da landing;
3. como configurar o convite do WhatsApp;
4. como testar localmente quando possível;
5. como configurar o Git no hPanel;
6. checklist de deploy;
7. checklist pós-deploy;
8. qualquer pendência que dependa de acesso manual à Hostinger ou de assets finais.
