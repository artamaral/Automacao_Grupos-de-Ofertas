# Perfis de descoberta

Os filtros operacionais de coleta devem ficar em arquivo versionado, sem depender
de banco ou interface administrativa nesta fase.

O caminho padrão atual é:

```text
config/discovery_profiles.toml
```

Cada perfil concentra a entrada de negócio para a coleta:

- nicho canônico;
- marketplace padrão;
- query base para a API;
- marcas, creators e categorias de apoio;
- termos de inclusão e exclusão;
- target lógico padrão;
- limite sugerido por execução.

O perfil também deve ser pensado como ponte para a identidade operacional do
nicho. Hoje o projeto já possui a decisão de manter contas de email separadas
para `feminino`, `mãe e bebê`, `auto e moto` e `achadinhos geral`. Mesmo antes de
existirem campos explícitos para isso no arquivo, essa separação serve apenas
como contexto operacional documentado. As contas ainda não fazem parte da lógica
de descoberta e não devem dirigir os filtros atuais dos perfis.

Exemplo de uso no harness:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino
```

Exemplo com subgroup:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile auto-e-moto --subgroup limpeza
```

Exemplo com inspeção estruturada da coleta:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino --save-inspection-json .\tmp\feminino-inspection.json
```

Também é possível apontar outro arquivo:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino --profiles-file .\config\discovery_profiles.toml
```

Os perfis versionados atuais representam os grandes nichos operacionais:

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`
- `achadinhos-geral`

Os perfis também podem carregar texto de referência operacional, como listas de
categorias visíveis observadas manualmente na Shopee. Essas listas servem como
apoio para curadoria e evolução dos filtros, mas devem ser tratadas como
parciais e não exaustivas.

Além disso, os perfis podem registrar `subgroups` como recortes iniciais dentro
de cada macro-nicho. Nesta fase, esses subgrupos devem ser lidos como hipótese
de escopo operacional, útil para organizar a descoberta e a futura curadoria.
Eles ainda não são contrato final.

Regra importante:

- os `subgroups` valem como definição inicial de escopo;
- depois precisam ser validados contra a API real da Shopee;
- também precisam ser comparados com dados reais de retorno, cobertura e
  qualidade de ofertas antes de virarem regra rígida de coleta.

Regras atuais:

- `--niche` continua disponível para uso manual e debug rápido;
- `--profile` passa a ser o caminho recomendado para operação;
- `--subgroup` permite recortar um macro-nicho quando o profile já tiver essa
  taxonomia definida;
- `--save-inspection-json` salva metadados da coleta, ofertas normalizadas e
  snapshot do provider para análise posterior;
- o provider recebe a `query` derivada do perfil;
- o sistema preserva o `niche` canônico do perfil na oferta normalizada;
- `include_terms` e `exclude_terms` já podem filtrar a saída pós-coleta.

Decisão operacional:

- manter os perfis em texto estruturado e versionado enquanto não houver frontend;
- evitar `.env` para dados de operação;
- documentar contas e identidades operacionais sem acoplar isso à descoberta
  antes da hora;
- usar banco apenas quando houver necessidade real de edição multiusuário,
  histórico operacional ou interface dedicada.
