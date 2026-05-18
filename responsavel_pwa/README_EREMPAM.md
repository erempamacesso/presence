# EREM PAM Família

PWA Flutter para responsáveis acompanharem comunicados do estudante.

## 1. Criar tabelas no Supabase

Execute o arquivo:

```text
responsavel_pwa/supabase_schema.sql
```

Ele cria:

- `notificacoes_responsaveis`
- `responsaveis_dispositivos`

## 2. Rodar localmente

Use a URL do projeto Supabase e a chave pública `anon`.

```powershell
flutter run -d chrome `
  --dart-define=SUPABASE_URL="https://SEU-PROJETO.supabase.co" `
  --dart-define=SUPABASE_ANON_KEY="SUA_ANON_KEY"
```

## 3. Gerar versão web/PWA

```powershell
flutter build web `
  --dart-define=SUPABASE_URL="https://SEU-PROJETO.supabase.co" `
  --dart-define=SUPABASE_ANON_KEY="SUA_ANON_KEY"
```

A saída fica em:

```text
responsavel_pwa/build/web
```

## 4. Fluxo atual

- Responsável entra com a matrícula do aluno.
- App consulta a tabela `alunos`.
- App lista comunicados em `notificacoes_responsaveis`.
- A tela de atrasos do Streamlit já cria notificação de atraso nessa tabela.

## 5. Push notification

Esta primeira versão já é PWA instalável e tem o centro de comunicados.

Para notificação que vibra/aparece no celular, o próximo passo é adicionar Web Push:

- cadastrar dispositivo em `responsaveis_dispositivos`;
- gerar chaves VAPID;
- criar uma Edge Function ou backend Python para enviar push;
- pedir permissão de notificação no PWA.
