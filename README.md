# Video Edition

Plataforma desktop para criar projetos do CapCut a partir de uma pasta de videos e aplicar acoes padronizadas de edicao.

## Estrutura

- `app/`: interface instalavel em Electron.
- `app/assets/`: logo e icones da plataforma.
- `scripts/`: automacoes que criam e ajustam drafts do CapCut.
- `config/`: perfis, presets e workflows editaveis.
- `examples/`: arquivos pequenos de exemplo.
- `docs/screenshots/`: prints usados como referencia durante o desenvolvimento.
- `build/dist/`: instaladores gerados.
- `.automation-work/`: area temporaria usada pelos scripts antigos/CLI.

## Uso Pela Plataforma

```powershell
npm start
```

Para gerar o instalador:

```powershell
npm run dist
```

O instalador sai em:

```text
build/dist/Video Edition-Setup-1.0.28.exe
```

## Fluxo Atual

A plataforma permite selecionar uma pasta de videos, escolher um projeto/modelo base do CapCut e marcar as acoes que devem ser aplicadas:

- cortar silencio inicial/final;
- reduzir ruido, normalizar e ajustar volume;
- aplicar efeitos e ajuste de cor;
- gerar e formatar legendas;
- inserir transicoes;
- inserir musica de fundo;
- ignorar arquivos especificos.

## Scripts Principais

- `scripts/Create-CapCutProjectFromProfile.py`: cria o projeto no CapCut a partir de um perfil.
- `scripts/Apply-CapCutDraftProfile.py`: aplica cortes, audio, legendas, efeitos, ajustes, transicoes e musica no draft.
- `scripts/Format-CaptionsFile.ps1`: rebalanceia legendas `.srt` em blocos curtos.

## Observacoes

- O CapCut precisa estar instalado na maquina.
- O Python precisa estar no `PATH`.
- As bibliotecas Python usadas pela automacao precisam estar instaladas no mesmo ambiente.
- Os perfis em `config/profiles/` podem ser duplicados para criar padroes por nicho, cliente ou pasta.
