# Video Downloader

Ferramenta para baixar um vídeo, extrair o áudio ou baixar uma playlist inteira usando o [yt-dlp](https://github.com/yt-dlp/yt-dlp). Dá para usar pela interface gráfica ou pela linha de comando.

Os arquivos vão, por padrão, para a pasta **Downloads do sistema** (`~/Downloads` no macOS e no Linux, a pasta Downloads do usuário no Windows). Nada é salvo dentro da pasta do projeto, a menos que você escolha outro destino.

## Requisitos

- Python 3.10 ou mais recente
- [ffmpeg](https://ffmpeg.org/) disponível no `PATH` (necessário para extrair áudio e para juntar vídeo e áudio)
- No macOS com Homebrew, o Python não traz o tkinter. Instale o pacote correspondente à sua versão, por exemplo:

```bash
brew install ffmpeg python-tk@3.14
```

## Instalação

No diretório do projeto:

```bash
python3 -m pip install --user -r requirements.txt
```

O `requirements.txt` instala:

- `yt-dlp`, que faz o download
- `curl-cffi`, usado pelo yt-dlp para imitar um navegador em sites que bloqueiam cliente comum

Use o mesmo `python3` na instalação e na execução. No macOS com Homebrew, o Python do sistema e o do Homebrew são interpretadores diferentes: um pacote instalado em um não aparece no outro. Se o `python3` do Homebrew for gerenciado externamente, o `--user` instala em `~/Library/Python/` sem alterar o Python do Homebrew.

## Interface gráfica

```bash
python3 ytdlp_ui.py
```

A janela tem:

| Campo | Função |
| --- | --- |
| URL | Endereço do vídeo ou da playlist |
| Tipo | Vídeo, áudio, playlist em vídeo ou playlist só em áudio |
| Qualidade | Altura máxima em pixels (1080, 720, etc.). "Melhor disponível" não limita. Vale só para vídeo |
| Formato | Formato do áudio (`mp3`, `m4a`, `wav`, `flac` ou `opus`). Vale só para áudio |
| Pasta | Destino dos arquivos. O padrão é a pasta Downloads do sistema |
| Escolher | Abre o seletor de pasta |
| Abrir | Abre a pasta de destino no gerenciador de arquivos |
| Baixar | Inicia o download sem travar a janela |
| Registro | Mensagens do yt-dlp, inclusive erro |

A barra mostra a porcentagem quando o tamanho do arquivo é conhecido. Sem tamanho, ela fica indeterminada. Em playlist, a barra acompanha o item que está sendo baixado.

O áudio sai na melhor qualidade disponível. Playlist em áudio usa o formato escolhido no campo Formato.

## Linha de comando

```bash
python3 ytdlp_helper.py video "URL"
python3 ytdlp_helper.py audio "URL"
python3 ytdlp_helper.py playlist "URL"
```

Opções:

```bash
python3 ytdlp_helper.py video "URL" --output-dir ~/Downloads --quality 1080
python3 ytdlp_helper.py audio "URL" --format mp3
python3 ytdlp_helper.py playlist "URL" --audio-only
python3 ytdlp_helper.py playlist "URL" --quality 720
```

| Comando | O que faz |
| --- | --- |
| `video` | Baixa um vídeo. Junta vídeo e áudio em MP4 quando o formato exige |
| `audio` | Extrai só o áudio. Padrão: MP3 |
| `playlist` | Baixa a playlist. Com `--audio-only`, extrai o áudio de cada item em MP3 |
| `--output-dir` | Pasta de destino. Padrão: Downloads do sistema |
| `--quality` | Altura máxima, em pixels (`720`, `1080`, …) |
| `--format` | Formato do áudio no comando `audio` |
| `--audio-only` | Na playlist, baixa só o áudio |
| `--menu` | Abre o menu de texto em vez dos subcomandos |

Sem argumentos, o script abre o mesmo menu de texto:

```bash
python3 ytdlp_helper.py
```

O programa também pode ser importado:

```python
from ytdlp_helper import download_video, download_audio, download_playlist

download_video("URL")
download_audio("URL", audio_format="mp3")
download_playlist("URL", audio_only=True)
```

Cada função devolve `True` quando termina e `False` quando falha.

## Onde os arquivos ficam

- Vídeo ou áudio avulso: `Downloads/<título>.<ext>`
- Playlist: `Downloads/<nome da playlist>/<índice> - <título>.<ext>`

A pasta é criada se ainda não existir.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `ytdlp_helper.py` | Download, menu de texto e linha de comando |
| `ytdlp_ui.py` | Interface gráfica em tkinter |
| `requirements.txt` | Dependências Python |
| `Video Downloader.spec` | Receita para gerar o aplicativo do macOS |

## Problemas comuns

**`ERRO: a biblioteca 'yt-dlp' não está instalada`**

O Python que rodou o script não tem o pacote. Instale de novo com esse mesmo interpretador:

```bash
python3 -m pip install --user -r requirements.txt
```

**`ffmpeg não encontrado no PATH`**

A extração de áudio e a junção de algumas faixas dependem do ffmpeg.

```bash
brew install ffmpeg
```

**Aviso de impersonation, ou o download não começa em alguns sites**

O extrator precisa imitar um navegador e o `curl-cffi` não está instalado nesse Python. Ele já está no `requirements.txt`. Reinstale as dependências com o mesmo `python3` usado para abrir o programa e rode de novo. Uma execução que começou antes da instalação não passa a enxergar o pacote.

**A interface não abre (`ModuleNotFoundError: tkinter`)**

Falta o tkinter nessa instalação do Python. No Homebrew:

```bash
brew install python-tk@3.14
```

Troque `3.14` pela versão que `python3 --version` mostrar.

**O arquivo não apareceu na pasta do projeto**

O destino padrão é a Downloads do sistema, não uma pasta `downloads` ao lado dos scripts. Use o botão Abrir na interface, ou confira `~/Downloads`.
