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

A implementação não deve reinterpretar estratégia, copy, identidade visual ou arquitetura já decididas.

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
11. tratamento de erro controlado quando o destino WhatsApp não estiver configurado ou for inválido;
12. pacote de produção pronto para upload manual no hPanel da Hostinger.

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
- testes A/B;
- integração automática GitHub → Hostinger.

## 4. Stack

Usar apenas:

- HTML5;
- CSS3;
- JavaScript vanilla quando necessário;
- PHP suportado pela Hostinger;
- `.htaccess` / `mod_rewrite` quando necessário;
- assets locais otimizados.

Evitar frameworks e dependências desnecessárias.

## 5. Estrutura de arquivos esperada

Estrutura equivalente à abaixo:

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
│   └── qr/
├── go/
│   └── whatsapp/
│       └── feminino.php
└── error/
    └── whatsapp-indisponivel.html
```

A configuração do convite não deve ficar no HTML ou JavaScript público.

O requisito obrigatório é **centralização do destino**, não sigilo absoluto. Se for simples no ambiente Hostinger, usar arquivo PHP dedicado para configuração. Não criar infraestrutura adicional apenas para esconder o convite.

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

Ao carregar `/feminino`, preservar nos CTAs apenas os parâmetros UTM suportados presentes na URL.

Exemplo:

```text
Entrada:
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01

CTA:
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
```

Regras:

- UTMs são opcionais;
- parâmetros ausentes não devem ser inventados;
- valores desconhecidos devem ser preservados como texto;
- ausência de UTM não pode quebrar a landing;
- não adicionar UTM ao link final `chat.whatsapp.com`;
- não persistir UTM em banco, cookie ou localStorage.

## 8. Redirect WhatsApp

O PHP deve:

1. carregar a configuração centralizada do nicho feminino;
2. verificar que existe;
3. verificar que não está vazia;
4. verificar que é URL HTTPS válida;
5. verificar formato/domínio aceito para convite WhatsApp;
6. responder HTTP `302` com `Location` quando válido;
7. interromper a execução após o redirect.

Não usar `301`.

Não colocar o convite diretamente:

- no HTML;
- em JavaScript;
- no QR Code;
- em anúncios;
- em múltiplos arquivos de configuração.

## 9. Falha controlada

Se o convite estiver ausente ou inválido:

- não redirecionar;
- não usar fallback silencioso;
- não redirecionar para outro nicho;
- não expor paths, variáveis, stack trace ou detalhes internos;
- apresentar página amigável de indisponibilidade.

Copy-base:

> O acesso ao grupo está temporariamente indisponível.
>
> Tente novamente em alguns minutos.

## 10. QR Code

Na versão desktop, exibir QR Code como mecanismo complementar.

O QR Code deve codificar:

```text
https://mktdigitalofertas.com.br/go/whatsapp/feminino
```

Nunca codificar diretamente `chat.whatsapp.com`.

- desktop: botão + QR Code podem coexistir;
- mobile: botão é prioritário e QR Code pode ser ocultado;
- QR Code institucional pode usar a rota sem UTM.

## 11. Wireframe obrigatório

Seguir `docs/landing-feminino-wireframe.md`.

Ordem:

1. Hero;
2. faixa de confiança;
3. macrogrupos;
4. Como funciona;
5. prova de curadoria / exemplos reais;
6. Vitrine Shopee;
7. reforço de urgência real;
8. CTA final;
9. rodapé.

## 12. Copy obrigatória/base

Usar os textos consolidados em `docs/landing-v1-contract.md`.

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

Não introduzir quantidade fixa de mensagens por dia ou horários individuais de triggers.

## 13. Macrogrupos

Exibir exatamente:

- 💄 Beleza
- 👗 Moda
- 👠 Calçados
- 👜 Bolsas e acessórios
- 💇‍♀️ Cabelos
- 🧴 Skincare

Não alterar a taxonomia interna do projeto.

## 14. Sistema visual

Seguir `docs/landing-feminino-sistema-visual.md`.

Diretrizes essenciais:

- identidade Ofertas Femininas dominante;
- fundo creme/rosado claro;
- coral/terracota nos CTAs;
- vinho/vermelho escuro nos títulos;
- rosa/pêssego nos blocos secundários;
- serifada elegante para títulos;
- sans-serif legível para textos;
- banner institucional das quatro mulheres como referência do Hero;
- peça de oferta como referência de cards e linguagem comercial;
- Shopee e Amazon visualmente subordinadas à marca.

## 15. Assets

Referências oficiais:

1. banner institucional Ofertas Femininas com quatro mulheres;
2. peça visual de oferta/produto fornecida na definição visual.

Usar assets existentes no repositório se já existirem. Caso não existam, deixar caminhos/estrutura claramente preparados e documentar onde inserir os arquivos. Não inventar arquivos como se já existissem.

Otimizar imagens para web quando apropriado.

## 16. Cards de prova de curadoria

Criar estrutura para aproximadamente 3 a 4 cards.

Cada card deve suportar:

- imagem;
- nome;
- marketplace;
- preço/oferta quando real;
- cupom quando real;
- CTA secundário.

CTAs possíveis:

- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calçados`;
- `Ver nossa seleção na Shopee`.

Não inventar preço, estoque, desconto ou validade. Se não houver exemplos reais definidos, usar placeholders claramente identificados no código e facilmente substituíveis.

## 17. Vitrine Shopee

A Vitrine Shopee é secundária.

CTA-base:

> Ver nossa seleção na Shopee

Hierarquia visual:

```text
WhatsApp > Vitrine Shopee > oferta/cupom individual
```

## 18. Responsividade

### Mobile

- CTA principal aparece cedo;
- Hero não é dominado pela ilustração;
- seções empilhadas;
- macrogrupos compactos;
- cards responsivos;
- QR Code pode ser ocultado;
- botões com área de toque adequada.

### Desktop

- Hero em duas colunas quando adequado;
- copy à esquerda e asset institucional à direita;
- botão WhatsApp + QR Code podem coexistir;
- cards em grid responsivo.

## 19. CTA fixo mobile

CTA fixo inferior é **opcional**.

Se implementado:

- não pode ser invasivo;
- não pode cobrir conteúdo;
- deve preservar UTMs;
- deve ser fácil de desativar.

## 20. `.htaccess` e URLs limpas

Configurar apenas o necessário.

- evitar loops;
- não transformar o redirect WhatsApp em permanente;
- manter `.htaccess` mínimo se a estrutura física de diretórios já resolver as URLs.

## 21. SEO e acessibilidade mínimos

Incluir:

- `<title>`;
- meta description;
- viewport;
- `lang="pt-BR"`;
- headings semânticos;
- `alt` em imagens relevantes;
- foco de teclado visível;
- contraste suficiente;
- botões/links semanticamente corretos;
- alternativa textual ao QR Code.

## 22. Performance

- sem bibliotecas grandes desnecessárias;
- imagens otimizadas;
- JS mínimo;
- sem autoplay de vídeo;
- poucas fontes;
- evitar efeitos pesados;
- priorizar carregamento móvel rápido.

## 23. Segurança e robustez

- validar qualquer valor usado pelo PHP;
- não construir `Location` com entrada arbitrária do visitante;
- destino vem somente da configuração controlada;
- não expor erros internos;
- não ativar display de erros PHP em produção;
- UTM é apenas dado textual de navegação.

## 24. Versionamento e deploy manual na Hostinger

GitHub permanece como fonte de verdade do código, mas **não existe integração GitHub → Hostinger para esta implantação**.

Fluxo oficial:

```text
GitHub
  ↓
branch/revisão/commit aprovado
  ↓
gerar pacote de produção
  ↓
validar pacote
  ↓
Hostinger hPanel / Gerenciador de Arquivos
  ↓
upload manual
  ↓
extrair/copiar para public_html
  ↓
testes pós-deploy
```

FTP pode ser usado como alternativa manual se necessário.

## 25. Pacote de produção obrigatório

A implementação deve gerar ou deixar pronta uma forma simples e reproduzível de gerar um pacote contendo somente o necessário para produção.

Conteúdo esperado:

```text
deploy/
└── public_html/
    ├── .htaccess
    ├── feminino/
    ├── assets/
    ├── go/
    └── error/
```

O nome exato da pasta de preparação pode variar, mas o conteúdo final deve poder ser copiado de forma simples para `public_html`.

O pacote não deve incluir:

- `.git`;
- documentação;
- arquivos de desenvolvimento não necessários;
- outros módulos do projeto;
- segredos desnecessários;
- código de n8n, catálogo, Supabase ou automações não relacionadas.

Se houver arquivo de configuração do convite que precise ser ajustado manualmente, documentar exatamente:

- caminho;
- formato;
- valor esperado;
- momento em que deve ser configurado.

## 26. Estado atual do domínio

`https://mktdigitalofertas.com.br/` está operacional e apresenta apenas a página padrão da hospedagem.

Antes do primeiro upload:

- verificar o conteúdo atual de `public_html`;
- manter backup simples dos arquivos existentes antes de substituir;
- não apagar arquivos desconhecidos sem inspeção.

## 27. Checklist de deploy manual

Antes do upload:

1. confirmar commit/versionamento da versão a publicar;
2. gerar pacote de produção;
3. revisar o conteúdo do pacote;
4. confirmar configuração do convite;
5. confirmar que `.htaccess` está incluído quando necessário;
6. confirmar que assets necessários estão presentes;
7. criar backup do conteúdo atual de `public_html`.

Publicação:

8. subir o pacote pelo hPanel;
9. extrair/copiar o conteúdo para `public_html`;
10. conferir permissões/estrutura se necessário;
11. não executar mudanças fora do diretório da landing sem necessidade.

Pós-deploy:

12. abrir `/feminino`;
13. testar CTA;
14. testar redirect `302`;
15. testar QR Code;
16. testar mobile e desktop;
17. testar URL com UTM;
18. verificar HTTPS;
19. confirmar que não há erros visíveis de PHP ou assets quebrados.

## 28. Testes obrigatórios

### Landing

1. `/feminino` sem query string;
2. `/feminino` com UTMs completas;
3. UTMs parciais;
4. mobile;
5. desktop;
6. imagens/fontes;
7. CTAs.

### UTM

8. CTA preserva UTMs até `/go/whatsapp/feminino`;
9. ausência de UTM não cria parâmetros vazios desnecessários.

### Redirect

10. HTTP `302`;
11. `Location` aponta para grupo configurado;
12. trocar configuração muda destino sem editar landing;
13. configuração ausente;
14. configuração inválida;
15. ausência de fallback silencioso.

### QR Code

16. escanear em celular real;
17. confirmar rota controlada;
18. confirmar independência do convite real.

### Visual

19. coerência com assets Ofertas Femininas;
20. WhatsApp é CTA dominante;
21. Shopee/ofertas individuais são secundários;
22. não há promessa de volume diário fixo ou horários individuais de triggers.

### Pacote

23. pacote contém somente arquivos de produção necessários;
24. pacote pode ser copiado para `public_html` sem depender do repositório inteiro;
25. instruções de configuração/publicação estão claras.

## 29. Critérios de aceite

A implementação está pronta quando:

1. `/feminino` carrega corretamente;
2. layout segue o wireframe;
3. identidade segue o sistema visual;
4. copy-base está correta;
5. funciona em mobile e desktop;
6. CTAs preservam UTMs;
7. `/go/whatsapp/feminino` retorna `302` para destino configurado;
8. convite real não está no HTML/JS nem no QR Code;
9. trocar convite exige alterar somente a configuração centralizada;
10. erro de configuração gera falha controlada;
11. QR Code desktop funciona;
12. não há dependência de banco, WordPress, Node.js ou serviços externos obrigatórios;
13. existe pacote de produção pronto para upload manual;
14. existe checklist de upload e pós-deploy;
15. todos os testes relevantes passam.

## 30. Instrução para o Codex

Implementar esta spec de forma incremental e conservadora.

### Regras

- Ler integralmente os quatro documentos referenciados na seção 1.
- Não alterar regras de negócio, copy aprovada, wireframe ou identidade sem solicitação explícita.
- Não adicionar frameworks ou infraestrutura fora do escopo.
- Não modificar workflows, automações, catálogo, n8n, Supabase ou outras áreas do projeto.
- Trabalhar somente nos arquivos necessários para a landing e redirect.
- Manter convite centralizado e fora do HTML/JS.
- Preservar UTM de forma simples e testável.
- Gerar QR Code a partir da rota estável, nunca do convite real.
- Preparar pacote de produção para upload manual na Hostinger.
- **Não fazer deploy real.**
- **Não configurar integração Git da Hostinger.**
- Não sobrescrever nem manipular o servidor Hostinger.

### Resultado esperado do Codex

Ao finalizar, apresentar:

1. arquivos criados/alterados;
2. arquitetura final;
3. como configurar e trocar o convite do WhatsApp;
4. como testar localmente quando possível;
5. caminho/estrutura do pacote de produção;
6. como gerar o pacote novamente;
7. checklist de upload manual no hPanel;
8. checklist pós-deploy;
9. qualquer pendência de assets ou configuração externa.
