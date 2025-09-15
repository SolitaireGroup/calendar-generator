# calendar-generator

------------------

# 📅 Gerador de Calendário Escolar

Um aplicativo que converte imagens de horários escolares em eventos do Google Calendar ou arquivos .ics.

## 🚀 Funcionalidades

- **OCR Inteligente**: Extrai horários escolares de imagens usando Tesseract
- **Google Calendar**: Cria eventos diretamente no seu calendário
- **Arquivos .ics**: Gera arquivos de calendário para importação
- **Interface Web**: Interface amigável com Streamlit
- **Limpeza Automática**: Remove eventos antigos antes de criar novos

## 📋 Pré-requisitos

### Software Necessário
- Python 3.7+
- Tesseract OCR
- Conta do Google (para usar Google Calendar)

### Instalação do Tesseract

**Windows:**
```bash
# Via Chocolatey
choco install tesseract

# Ou baixe de: https://github.com/UB-Mannheim/tesseract/wiki
```

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

## 🛠️ Instalação

1. **Clone o repositório:**
```bash
git clone <url-do-repositorio>
cd calendar_generator
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Configure o Google Calendar (opcional):**
   - Vá para [Google Cloud Console](https://console.cloud.google.com/)
   - Crie um novo projeto ou selecione um existente
   - Habilite a API do Google Calendar
   - Vá para "Credenciais" e crie credenciais OAuth 2.0
   - Baixe o arquivo JSON e renomeie para `credentials.json`
   - Coloque o arquivo na pasta do projeto

## 🎯 Como Usar

### Interface Web (Recomendado)
```bash
streamlit run app.py
```

### Linha de Comando
```bash
# Gerar arquivo .ics
python main.py horario.jpg 2024-12-31

# Criar eventos no Google Calendar
python main.py horario.jpg --google-calendar
```

## 🧪 Testes

Execute o script de teste para verificar se tudo está funcionando:

```bash
python teste_google_calendar.py
```

## 📁 Estrutura do Projeto

```
calendar_generator/
├── app.py                      # Interface web Streamlit
├── main.py                     # Lógica principal
├── google_calendar_manager.py  # Gerenciamento do Google Calendar
├── calendar_manager.py         # Gerenciamento de calendários
├── parser/
│   └── parser.py              # Parser de horários escolares
├── credentials_example.json   # Exemplo de credenciais
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

## 🔧 Configuração Avançada

### Personalizar Horários
Edite o arquivo `parser/parser.py` para ajustar:
- Horários das aulas
- Dias da semana
- Matérias reconhecidas

### Personalizar Eventos
Edite `google_calendar_manager.py` para ajustar:
- Descrição dos eventos
- Fuso horário
- Configurações de recorrência
