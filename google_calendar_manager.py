import os
import json
from datetime import datetime, timedelta, timezone, time
from typing import List, Dict, Optional

import logging
logger = logging.getLogger(__name__)

DIA_COR = {
    "segunda": "1",  # azul
    "terça": "2",    # verde
    "quarta": "3",   # roxo
    "quinta": "4",   # vermelho
    "sexta": "5"     # amarelo
}

class GoogleCalendarManager:
    """
    Gerencia eventos no Google Calendar
    """
    
    def __init__(self):
        self.service = None
        self.calendar_id = 'primary'
        
    def authenticate(self):
        """
        Autentica com o Google Calendar
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            CREDENTIALS_FILE = 'credentials.json'
            TOKEN_FILE = 'token.json'
            
            creds = None
            
            # Verifica se já existe token salvo
            if os.path.exists(TOKEN_FILE):
                try:
                    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                    logger.info("Token carregado do arquivo")
                except Exception as e:
                    logger.warning(f"Erro ao carregar token: {e}")
                    creds = None
            
            # Se não há credenciais válidas, faz login
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Token renovado com sucesso")
                    except Exception as e:
                        logger.warning(f"Erro ao renovar token: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(CREDENTIALS_FILE):
                        raise FileNotFoundError(f"Arquivo {CREDENTIALS_FILE} não encontrado! Baixe o arquivo de credenciais do Google Cloud Console.")
                    
                    logger.info("Iniciando processo de autenticação...")
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    # Usa porta fixa para evitar problemas de redirecionamento
                    creds = flow.run_local_server(port=8080, open_browser=True)
                    logger.info("Autenticação concluída")
                
                # Salva as credenciais para próxima vez
                try:
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Token salvo para uso futuro")
                except Exception as e:
                    logger.warning(f"Erro ao salvar token: {e}")
            
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Autenticado com Google Calendar")
            
        except FileNotFoundError as e:
            logger.error(f"❌ Arquivo de credenciais não encontrado: {e}")
            logger.error("Para usar o Google Calendar, você precisa:")
            logger.error("1. Ir ao Google Cloud Console")
            logger.error("2. Criar um projeto e habilitar a API do Calendar")
            logger.error("3. Criar credenciais OAuth 2.0")
            logger.error("4. Baixar o arquivo credentials.json")
            raise
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {e}")
            raise
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime, dia_semana: str, recurrence: List[str] = None, until: datetime = None) -> str:
        """
        Cria um novo evento no Google Calendar
        """
        if not self.service:
            self.authenticate()
        
        color_id = DIA_COR.get(dia_semana.lower(), "1")
        event = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            'colorId': color_id,
        }
        if recurrence and until:
            event['recurrence'] = [f"RRULE:FREQ=WEEKLY;UNTIL={until.strftime('%Y%m%dT%H%M%SZ')}"]
        
        try:
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"✅ Evento criado: {title} - {dia_semana} ({created_event['id']})")
            return created_event['id']
            
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            raise
    
    def delete_events_by_description(self, description_pattern: str = "[ESCOLA] [HORARIO_ESCOLAR]", start_date: datetime = None):
        """
        Deleta eventos que contenham o padrão na descrição a partir de start_date
        """
        if not self.service:
            self.authenticate()
        
        if start_date is None:
            start_date = datetime.now(timezone.utc)
        
        try:
            # Busca eventos com o padrão na descrição
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                q=description_pattern,
                maxResults=1000
            ).execute()
            
            events = events_result.get('items', [])
            deleted_count = 0
            
            for event in events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                # event_start = ... (já deve estar com tzinfo=timezone.utc)
                if event_start >= start_date:
                    try:
                        self.service.events().delete(
                            calendarId=self.calendar_id,
                            eventId=event['id']
                        ).execute()
                        deleted_count += 1
                        logger.info(f"Evento deletado: {event.get('summary', 'Sem título')}")
                    except Exception as e:
                        logger.error(f"Erro ao deletar evento {event.get('id')}: {e}")
            
            logger.info(f"Total de eventos deletados: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erro ao buscar/deletar eventos: {e}")
            raise
    
    def list_events_by_description(self, description_pattern: str = "[ESCOLA] [HORARIO_ESCOLAR]"):
        """
        Lista eventos que contenham o padrão de descrição especificado
        """
        if not self.service:
            self.authenticate()
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                q=description_pattern,
                maxResults=1000
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Encontrados {len(events)} eventos com padrão '{description_pattern}'")
            
            for event in events:
                logger.info(f"- {event.get('summary', 'Sem título')} ({event.get('id')})")
            
            return events
            
        except Exception as e:
            logger.error(f"Erro ao listar eventos: {e}")
            raise

    def delete_all_school_events(self, description_pattern="[ESCOLA] [HORARIO_ESCOLAR]"):
        """
        Deleta todos os eventos escolares do Google Calendar que contenham o padrão na descrição
        """
        events_result = self.service.events().list(
            calendarId='primary',
            q=description_pattern,
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])
        deleted_count = 0
        for event in events:
            try:
                self.service.events().delete(calendarId='primary', eventId=event['id']).execute()
                deleted_count += 1
                logger.info(f"Evento deletado: {event.get('summary', '')}")
            except Exception as e:
                logger.error(f"Erro ao deletar evento: {e}")
        logger.info(f"Total de eventos deletados: {deleted_count}")
        return deleted_count

    def delete_all_events(self):
        """
        Deleta TODOS os eventos futuros do Google Calendar principal (a partir de hoje 00:00 UTC), incluindo recorrentes
        """
        if not self.service:
            self.authenticate()
        today = datetime.combine(datetime.now(timezone.utc).date(), time(0, 0), tzinfo=timezone.utc)
        deleted_count = 0
        page_token = None
        # Primeiro, deleta todas as instâncias futuras
        while True:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=today.isoformat(),
                singleEvents=True,  # pega todas as instâncias futuras
                maxResults=1000,
                pageToken=page_token
            ).execute()
            events = events_result.get('items', [])
            for event in events:
                try:
                    self.service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    deleted_count += 1
                    logger.info(f"Evento deletado: {event.get('summary', '')}")
                except Exception as e:
                    logger.error(f"Erro ao deletar evento: {e}")
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        # Agora, deleta os eventos "pais" recorrentes futuros
        page_token = None
        while True:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=today.isoformat(),
                singleEvents=False,  # pega eventos recorrentes "pais"
                maxResults=1000,
                pageToken=page_token
            ).execute()
            events = events_result.get('items', [])
            for event in events:
                if 'recurrence' in event:
                    try:
                        self.service.events().delete(calendarId='primary', eventId=event['id']).execute()
                        deleted_count += 1
                        logger.info(f"Evento recorrente deletado: {event.get('summary', '')}")
                    except Exception as e:
                        logger.error(f"Erro ao deletar evento recorrente: {e}")
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        logger.info(f"Total de eventos deletados: {deleted_count}")
        return deleted_count

    def get_all_events(self):
        """
        Retorna todos os eventos futuros do calendário principal (a partir de hoje 00:00 UTC)
        """
        if not self.service:
            self.authenticate()
        today = datetime.combine(datetime.now(timezone.utc).date(), time(0, 0), tzinfo=timezone.utc)
        events = []
        page_token = None
        while True:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=today.isoformat(),
                singleEvents=True,
                maxResults=1000,
                pageToken=page_token
            ).execute()
            items = events_result.get('items', [])
            events.extend(items)
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        return events

    def create_weekly_event(self, materia: str, start_datetime: datetime, end_datetime: datetime, weekday_num: int, end_date: str) -> str:
        """
        Cria um evento semanal no Google Calendar para a matéria especificada
        """
        if not self.service:
            self.authenticate()
        
        # Mapeia o número do dia da semana para o formato do Google Calendar (MO, TU, WE, TH, FR)
        dia_semana_abrev = self._get_weekday_abbr(weekday_num)
        
        try:
            event_id = self.google_manager.create_event(
                title=materia,
                start_time=start_datetime,
                end_time=end_datetime,
                recurrence=[f"RRULE:FREQ=WEEKLY;BYDAY={dia_semana_abrev}"],
                until=datetime.strptime(end_date, "%Y-%m-%d")
            )
            logger.info(f"✅ Evento semanal criado: {materia} ({event_id})")
            return event_id
        except Exception as e:
            logger.error(f"Erro ao criar evento semanal: {e}")
            raise

    def _get_weekday_abbr(self, weekday_num: int) -> str:
        """
        Retorna a abreviação do dia da semana em inglês (MO, TU, WE, TH, FR) com base no número do dia da semana
        """
        # O Google Calendar usa a seguinte convenção para os dias da semana:
        # MO - Monday
        # TU - Tuesday
        # WE - Wednesday
        # TH - Thursday
        # FR - Friday
        # SA - Saturday
        # SU - Sunday
        weekday_abbr = {
            0: "MO",
            1: "TU",
            2: "WE",
            3: "TH",
            4: "FR",
            5: "SA",
            6: "SU"
        }
        return weekday_abbr.get(weekday_num, "MO")

