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

## 4. Publicar na Vercel

Instale a CLI da Vercel se ainda não tiver:

```powershell
npm install -g vercel
```

Gere o build:

```powershell
flutter build web `
  --dart-define=SUPABASE_URL="https://SEU-PROJETO.supabase.co" `
  --dart-define=SUPABASE_ANON_KEY="SUA_ANON_KEY"
```

Copie a configuração da Vercel para a pasta publicada:

```powershell
Copy-Item .\vercel.json .\build\web\vercel.json -Force
```

Publique a pasta gerada:

```powershell
cd build\web
vercel --prod
```

Na primeira vez, a Vercel vai pedir login e algumas confirmações. Aceite publicar como projeto novo.

## 5. Fluxo atual

- Responsável entra com a matrícula do aluno.
- Responsável também pode pesquisar pelo início do nome do aluno.
- App consulta a tabela `alunos`.
- App lista comunicados em `notificacoes_responsaveis`.
- A tela de atrasos do Streamlit já cria notificação de atraso nessa tabela.

## 6. Push notification

Esta primeira versão já é PWA instalável e tem o centro de comunicados.

Para notificação que vibra/aparece no celular, o próximo passo é adicionar Web Push:

- cadastrar dispositivo em `responsaveis_dispositivos`;
- gerar chaves VAPID;
- criar uma Edge Function ou backend Python para enviar push;
- pedir permissão de notificação no PWA.
