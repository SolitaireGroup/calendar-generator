import streamlit as st
import os
from pathlib import Path
from datetime import date, datetime, timedelta
from main import CalendarGenerator
from google_calendar_manager import GoogleCalendarManager
import time
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="📅 Gerador de Calendário Escolar",
    page_icon="📅",
    layout="wide"
)

# Título Principal
st.title("📅 Gerador de Calendário Escolar")
st.markdown("Bem-vindo! Este aplicativo transforma a imagem do seu horário escolar em eventos no Google Calendar.")
st.markdown("---")

# --- PASSO 1: Upload da Imagem ---
st.header("1. Faça o upload da sua imagem")
uploaded_file = st.file_uploader(
    "Escolha uma imagem do horário escolar",
    type=['png', 'jpg', 'jpeg'],
    help="Formatos suportados: PNG, JPG, JPEG"
)

if uploaded_file is not None:
    # Mostra a imagem enviada
    st.image(uploaded_file, caption='Imagem do horário enviada', use_column_width=True)
    st.markdown("---")

    # --- PASSO 2: Processamento e Edição ---
    st.header("2. Revise o texto extraído")
    st.info("O aplicativo está processando a imagem. Aguarde um momento...")
    
    with st.spinner('Extraindo texto da imagem...'):
        # Salva o arquivo temporariamente para o parser
        file_path = Path("temp_image.png")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Instancia o gerador de calendário (sem o Google Calendar por enquanto)
        generator = CalendarGenerator(use_google_calendar=False)

        try:
            # Usa o parser para extrair o horário
            schedule = generator.parser.parse_schedule(str(file_path))
            os.remove(file_path) # Remove o arquivo temporário

            # Converte o dicionário do horário para um formato de texto editável
            schedule_text = ""
            for day, classes in schedule.items():
                schedule_text += f"{day}: {', '.join(classes)}\n"

            # Campo de texto para o usuário revisar e editar
            edited_schedule_text = st.text_area(
                "Texto extraído da imagem (você pode editar aqui):",
                value=schedule_text,
                height=250
            )

            # --- PASSO 3: Configurações e Geração ---
            st.markdown("---")
            st.header("3. Configure e gere seu calendário")
            
            # Layout de colunas para as opções
            col1, col2 = st.columns(2)

            with col1:
                end_date = st.date_input(
                    "Data de fim do calendário",
                    value=date(2025, 12, 12),
                    help="Data final para os eventos recorrentes"
                )
            
            with col2:
                use_google_calendar = st.checkbox(
                    "Criar eventos no Google Calendar",
                    value=True,
                    help="Cria eventos diretamente no seu Google Calendar"
                )

            # Botão principal
            if st.button("🚀 Gerar Calendário"):
                # Re-parse o texto editado de volta para o dicionário
                edited_schedule = {}
                for line in edited_schedule_text.split('\n'):
                    if ':' in line:
                        day, classes_str = line.split(':', 1)
                        edited_schedule[day.strip()] = [c.strip() for c in classes_str.split(',')]
                
                # Instancia o gerador com a opção de Google Calendar
                generator = CalendarGenerator(use_google_calendar=use_google_calendar)

                with st.spinner('Gerando eventos...'):
                    generator.generate_from_schedule(
                        schedule=edited_schedule,
                        end_date=end_date.strftime("%Y-%m-%d")
                    )

                st.success("✅ Calendário gerado com sucesso!")
                
        except Exception as e:
            st.error(f"❌ Ocorreu um erro no processamento: {e}")
            logger.error(f"Erro no processamento: {e}")

# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações e Ferramentas")

st.sidebar.subheader("Limpeza do calendário")
st.sidebar.info("Atenção: A limpeza é irreversível.")
if st.sidebar.button("Apagar todos os eventos futuros"):
    google_manager = GoogleCalendarManager()
    google_manager.authenticate()
    with st.spinner('Apagando eventos futuros...'):
        deleted_count = google_manager.delete_all_future_events()
    st.sidebar.success(f"✅ {deleted_count} eventos futuros apagados!")

st.sidebar.subheader("Limpar um dia específico")
selected_day = st.sidebar.date_input("Escolha o dia para apagar eventos", value=date.today())
if st.sidebar.button("Apagar eventos desse dia"):
    google_manager = GoogleCalendarManager()
    google_manager.authenticate()
    start = datetime.combine(selected_day, datetime.min.time()).isoformat() + 'Z'
    end = (datetime.combine(selected_day, datetime.max.time()) + timedelta(seconds=-1)).isoformat() + 'Z'
    events = google_manager.service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        maxResults=1000
    ).execute().get('items', [])
    deleted_count = 0
    for event in events:
        try:
            google_manager.service.events().delete(calendarId='primary', eventId=event['id']).execute()
            deleted_count += 1
            logger.info(f"Evento deletado: {event.get('summary', '')}")
        except Exception as e:
            logger.error(f"Erro ao deletar evento: {e}")
            
    st.sidebar.success(f"✅ {deleted_count} eventos do dia {selected_day.strftime('%d/%m/%Y')} apagados!")
