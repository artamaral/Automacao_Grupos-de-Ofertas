# Landing Ofertas Femininas — pacote Hostinger

O conteúdo de `deploy/public_html/` é o pacote de produção. Ele pode ser copiado diretamente para o `public_html` da hospedagem, sem levar o restante do repositório.

## Configurar ou trocar o convite do WhatsApp

O convite informado em 27/08/2026 já está configurado na fonte única abaixo.

1. Abra `deploy/public_html/_config/whatsapp.php`.
2. Para trocar o grupo, altere somente o valor de `WHATSAPP_GROUP_URL_FEMININO`.
3. Use um convite no formato `https://chat.whatsapp.com/CODIGO_DO_CONVITE`.
4. Salve o arquivo, gere o ZIP novamente e teste a rota antes de divulgar a landing.

O convite fica apenas nesse arquivo. Não o adicione ao HTML, JavaScript, QR Code ou outros arquivos. Para trocar o grupo futuramente, altere somente esse valor e reenvie `_config/whatsapp.php`.

## Link da seleção Shopee

O botão `Ver nossa seleção na Shopee` aponta para `https://collshp.com/ofertas_femininas`. Ao trocar a vitrine, atualize o endereço no HTML, gere o ZIP novamente e valide o destino antes de publicar.

## Gerar o ZIP novamente

No PowerShell, a partir da raiz do repositório:

```powershell
.\scripts\build_landing_feminino_package.ps1
```

O comando valida a estrutura e cria `deploy/landing-feminino-public-html.zip`. O ZIP contém a pasta `public_html` e somente arquivos de produção.

## Upload manual no hPanel

1. Confirme o commit aprovado e gere o ZIP.
2. No hPanel, abra o Gerenciador de Arquivos e inspecione o `public_html` atual.
3. Faça um backup dos arquivos existentes antes de substituir qualquer item.
4. Confirme que o convite ativo continua configurado em `_config/whatsapp.php`.
5. Envie o ZIP e extraia seu conteúdo.
6. Copie o conteúdo da pasta extraída `public_html` para o `public_html` real.
7. Preserve arquivos desconhecidos até confirmar se podem ser substituídos.
8. Não envie `.git`, `docs`, catálogos, workflows, n8n ou Supabase.

## Checklist pós-deploy

- Abra `https://mktdigitalofertas.com.br/feminino` no celular e no desktop.
- Repita com UTMs completas e parciais; confirme que os CTAs as preservam.
- Verifique se o QR Code abre `https://mktdigitalofertas.com.br/go/whatsapp/feminino`.
- Execute `curl -I https://mktdigitalofertas.com.br/go/whatsapp/feminino` e confirme `HTTP 302` e o `Location` configurado.
- Remova temporariamente o valor do convite e confirme uma página amigável com HTTP 503, sem redirect.
- Teste também um valor HTTP ou domínio diferente e confirme a mesma falha controlada.
- Confirme HTTPS, assets sem erro e ausência de mensagens internas do PHP.

## Pendências antes da publicação

- Escanear o QR Code em um celular real.
