@echo off
echo Atualizando repositorio no GitHub...
git add .
git commit -m "ajuste no codigo"
git push origin main
echo Processo concluido. Verifique o status em https://vercel.com