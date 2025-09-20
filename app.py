import streamlit as st
import os
from pathlib import Path
from datetime import date, datetime, timedelta
from main import CalendarGenerator
from google_calendar_manager import GoogleCalendarManager
import time
import logging

logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="📅 Gerador de Calendário Escolar",
    page_icon="📅",
    layout="wide"
)

# Título
st.title("📅 Gerador de Calendário Escolar")
st.markdown("**Arraste e solte** uma imagem do horário escolar!")

# Sidebar
st.sidebar.header("⚙️ Configurações")

# Data de fim do calendário
end_date = st.sidebar.date_input(
    "Data de fim do calendário",
    value=date(2025, 12, 12),
    help="Data final para os eventos recorrentes"
)

# Opção de usar Google Calendar
use_google_calendar = st.sidebar.checkbox(
    "Criar eventos no Google Calendar",
    value=True,
    help="Cria eventos diretamente no seu Google Calendar"
)

# Upload de arquivo
uploaded_file = st.file_uploader(
    "Escolha uma imagem do horário escolar",
    type=['png', 'jpg', 'jpeg'],
    help="Formatos suportados: PNG, JPG, JPEG"
)

if uploaded_file is not None:
    # Mostra a imagem
    st.image(uploaded_file, caption="Imagem carregada", use_column_width=True)
    
    # Estado para controlar o fluxo
    if 'processing_stage' not in st.session_state:
        st.session_state.processing_stage = 'upload'
    
    if st.session_state.processing_stage == 'upload':
        if st.button("🚀 Processar Imagem", type="primary"):
            try:
                # Salva o arquivo temporariamente
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Processa a imagem
                with st.spinner("🔄 Processando imagem..."):
                    generator = CalendarGenerator(use_google_calendar=use_google_calendar, turno="manha")
                    raw_text = generator.parser.extract_text_from_image(temp_path)
                    
                    # Salva no estado da sessão
                    st.session_state.temp_path = temp_path
                    st.session_state.generator = generator
                    st.session_state.raw_text = raw_text
                    st.session_state.processing_stage = 'review'
                    
            except Exception as e:
                st.error(f"❌ Erro ao processar imagem: {str(e)}")
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
    
    elif st.session_state.processing_stage == 'review':
        # Campo editável para o usuário revisar/corrigir
        edited_text = st.text_area("Texto extraído (edite se necessário):", 
                                 value=st.session_state.raw_text, 
                                 height=300)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar e Gerar Calendário", type="primary"):
                try:
                    with st.spinner("✨ Gerando calendário..."):
                        # Usa o texto editado para gerar o calendário
                        result = st.session_state.generator.process_text(
                            edited_text, 
                            end_date.strftime("%Y-%m-%d")
                        )
                        
                        # Remove arquivo temporário
                        if os.path.exists(st.session_state.temp_path):
                            os.remove(st.session_state.temp_path)
                        
                        # Mostra resultado
                        st.session_state.result = result
                        st.session_state.processing_stage = 'result'
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Erro ao gerar calendário: {str(e)}")
                    if 'temp_path' in st.session_state and os.path.exists(st.session_state.temp_path):
                        os.remove(st.session_state.temp_path)
        
        with col2:
            if st.button("🔄 Tentar Novamente"):
                if 'temp_path' in st.session_state and os.path.exists(st.session_state.temp_path):
                    os.remove(st.session_state.temp_path)
                st.session_state.processing_stage = 'upload'
                st.rerun()
    
    elif st.session_state.processing_stage == 'result':
        st.success("✅ Calendário gerado com sucesso!")
        
        if use_google_calendar:
            st.info(f"📅 **Google Calendar:** {st.session_state.result}")
            st.markdown("""
            ### 🎉 Eventos criados no Google Calendar!
            
            Os eventos foram criados diretamente no seu Google Calendar e vão se repetir até **{}**.
            
            **Próximos passos:**
            1. Abra o [Google Calendar](https://calendar.google.com)
            2. Verifique se os eventos apareceram
            3. Ajuste os horários se necessário
            """.format(end_date.strftime("%d/%m/%Y")))
        else:
            # Mostra informações do arquivo .ics
            if os.path.exists(st.session_state.result):
                file_size = os.path.getsize(st.session_state.result)
                st.info(f"📁 Arquivo salvo: `{st.session_state.result}` ({file_size} bytes)")
                
                # Botão para download
                with open(st.session_state.result, "rb") as f:
                    st.download_button(
                        label="📥 Baixar arquivo .ics",
                        data=f.read(),
                        file_name=Path(st.session_state.result).name,
                        mime="text/calendar"
                    )
        
        if st.button("🔄 Processar Outra Imagem"):
            # Limpa o estado da sessão
            for key in ['processing_stage', 'temp_path', 'generator', 'raw_text', 'result']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

st.markdown("---")

st.sidebar.header("⚠️ Limpeza do calendário")
if st.sidebar.button("Apagar TODOS os eventos futuros"):
    google_manager = GoogleCalendarManager()
    google_manager.authenticate()
    # Busca todos os eventos futuros
    events = google_manager.get_all_events()
    # Organiza eventos por dia
    from collections import defaultdict
    eventos_por_dia = defaultdict(list)
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        dia = start[:10]  # yyyy-mm-dd
        eventos_por_dia[dia].append(event)
    deleted_count = 0
    for dia, eventos in sorted(eventos_por_dia.items()):
        for event in eventos:
            try:
                google_manager.service.events().delete(calendarId='primary', eventId=event['id']).execute()
                deleted_count += 1
                logger.info(f"Evento deletado: {event.get('summary', '')}")
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Erro ao deletar evento: {e}")
        # Aguarda mais tempo entre dias para evitar quota
        time.sleep(2)
    st.sidebar.success(f"{deleted_count} eventos futuros apagados (um dia por vez)!")

st.sidebar.header("⚠️ Limpeza do calendário por dia")
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
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Erro ao deletar evento: {e}")
    st.sidebar.success(f"{deleted_count} eventos apagados para {selected_day.strftime('%d/%m/%Y')}")
