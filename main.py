import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
from ics import Calendar, Event
from parser import ScheduleParser
from google_calendar_manager import GoogleCalendarManager

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DIA_COR = {
    "segunda": "1",
    "terca": "2",
    "terça": "2",  # aceita ambos
    "quarta": "3",
    "quinta": "4",
    "sexta": "5"
}

class CalendarGenerator:
    """
    Gerador de calendário a partir de horários escolares
    """
    
    def __init__(self, use_google_calendar: bool = False):
        self.parser = ScheduleParser()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.use_google_calendar = use_google_calendar
        self.google_manager = GoogleCalendarManager() if use_google_calendar else None
    
    def generate_ics_calendar(self, schedule: dict, end_date: str = None) -> str:
        """
        Gera arquivo .ics a partir do horário
        """
        if not end_date:
            end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        calendar = Calendar()
        time_slots = self.get_time_slots()
        
        dias = ["segunda", "terca", "quarta", "quinta", "sexta"]
        
        for dia, materias in schedule.items():
            if dia not in dias:
                continue
                
            weekday_num = dias.index(dia)
            
            for i, materia in enumerate(materias):
                if materia == "???" or materia.lower() == "recreio":
                    continue
                
                today = datetime.now()
                days_ahead = weekday_num - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                
                start_date = today + timedelta(days=days_ahead)
                time_slot = time_slots[i]
                start_time, end_time = time_slot.split('-')
                
                start_datetime = datetime.combine(
                    start_date.date(),
                    datetime.strptime(start_time, "%H:%M").time()
                )
                
                end_datetime = datetime.combine(
                    start_date.date(), 
                    datetime.strptime(end_time, "%H:%M").time()
                )
                
                event = Event()
                event.name = materia
                event.begin = start_datetime
                event.end = end_datetime
                event.recurring = True
                event.until = datetime.strptime(end_date, "%Y-%m-%d")
                
                calendar.events.add(event)
                logger.info(f"Criado evento: {materia} - {dia} {time_slot}")
        
        return calendar
    
    def save_ics_file(self, calendar: Calendar, filename: str = None) -> str:
        """
        Salva o calendário em arquivo .ics
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"horario_escolar_{timestamp}.ics"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(calendar))
        
        logger.info(f"Arquivo .ics salvo em: {filepath}")
        return str(filepath)
    
    def create_google_calendar_events(self, schedule: dict, end_date: str = None) -> int:
        """
        Cria eventos diretamente no Google Calendar
        """
        if not end_date:
            end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        # Primeiro, deleta eventos antigos da escola
        try:
            deleted_count = self.google_manager.delete_events_by_description()
            logger.info(f"Eventos antigos deletados: {deleted_count}")
        except Exception as e:
            logger.warning(f"Não foi possível deletar eventos antigos: {e}")
        
        time_slots = self.parser.get_time_slots()
        dias = ["segunda", "terca", "terça", "quarta", "quinta", "sexta"]

        created_count = 0

        for dia, materias in schedule.items():
            if dia not in dias:
                continue
            dia_padrao = "terca" if dia in ["terca", "terça"] else dia
            weekday_num = ["segunda", "terca", "quarta", "quinta", "sexta"].index(dia_padrao)
            for i, materia in enumerate(materias):
                if materia == "???" or materia.lower() == "recreio":
                    continue
                
                today = datetime.now()
                dia_semana = DIA_COR.get(dia)
                
                time_slot = time_slots[i]
                start_time, end_time = time_slot.split('-')
                
                start_datetime = datetime.combine(
                    today.date(),
                    datetime.strptime(start_time, "%H:%M").time()
                )
                
                end_datetime = datetime.combine(
                    today.date(), 
                    datetime.strptime(end_time, "%H:%M").time()
                )
                
                # Ajusta o dia da semana
                if today.weekday() != int(dia_semana) - 1:
                    days_diff = int(dia_semana) - 1 - today.weekday()
                    if days_diff < 0:
                        days_diff += 7
                    start_datetime += timedelta(days=days_diff)
                    end_datetime += timedelta(days=days_diff)
                
                try:
                    event_id = self.google_manager.create_event(
                        title=materia,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        dia_semana=dia_padrao,
                        recurrence=[f"RRULE:FREQ=WEEKLY;BYDAY={self._get_weekday_abbr(weekday_num)}"],
                        until=datetime.strptime(end_date, "%Y-%m-%d")
                    )
                    created_count += 1
                    logger.info(f"✅ Evento criado: {materia} - {dia} {time_slot}")
                except Exception as e:
                    logger.error(f"❌ Erro ao criar evento {materia} - {dia} {time_slot}: {e}")
        
        return created_count
    
    def _get_weekday_abbr(self, weekday_num: int) -> str:
        """
        Converte número do dia da semana para abreviação do RRULE
        """
        abbr_map = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR'}
        return abbr_map.get(weekday_num, 'MO')
    
    def process_image(self, image_path: str, end_date: str = None) -> str:
        """
        Processa uma imagem de horário e gera o arquivo .ics
        """
        try:
            logger.info(f"Processando imagem: {image_path}")
            
            # Faz o parsing do horário
            schedule = self.parser.parse_schedule(image_path)
            logger.info(f"Horário extraído: {schedule}")
            
            if self.use_google_calendar:
                # Cria eventos diretamente no Google Calendar
                created_count = self.create_google_calendar_events(schedule, end_date)
                logger.info(f"Criados {created_count} eventos no Google Calendar")
                return f"Google Calendar: {created_count} eventos criados"
            else:
                # Gera arquivo .ics
                calendar = self.generate_ics_calendar(schedule, end_date)
                ics_file = self.save_ics_file(calendar)
                return ics_file
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem: {e}")
            raise

    def process_text(self, text: str, end_date: str):
        """
        Processa um texto de horário e gera o arquivo .ics
        """
        try:
            logger.info(f"Processando texto")
            
            # Faz o parsing do horário
            schedule = self.parser.parse_schedule_from_text(text)
            logger.info(f"Horário extraído: {schedule}")
            
            if self.use_google_calendar:
                # Cria eventos diretamente no Google Calendar
                created_count = self.create_google_calendar_events(schedule, end_date)
                logger.info(f"Criados {created_count} eventos no Google Calendar")
                return f"Google Calendar: {created_count} eventos criados"
            else:
                # Gera arquivo .ics
                calendar = self.generate_ics_calendar(schedule, end_date)
                ics_file = self.save_ics_file(calendar)
                return ics_file
            
        except Exception as e:
            logger.error(f"Erro ao processar texto: {e}")
            raise

    def get_time_slots(self):
        """
        Retorna os horários das aulas
        """
        return [
            "07:30-08:15",
            "08:16-09:00",
            "09:01-09:45",
            "10:01-10:45",
            "10:46-11:30"
        ]

def main():
    """
    Função principal para uso via linha de comando
    """
    if len(sys.argv) < 2:
        print("Uso: python main.py <imagem> [data_final] [--google-calendar]")
        return
    
    image_path = sys.argv[1]
    end_date = None
    use_google_calendar = False
    
    # Processa argumentos
    for arg in sys.argv[2:]:
        if arg.startswith("202"):
            end_date = arg
        if arg == "--google-calendar":
            use_google_calendar = True

    generator = CalendarGenerator(use_google_calendar=use_google_calendar)
    print("Processando imagem:", image_path)
    parser = ScheduleParser()
    schedule = parser.parse_schedule(image_path)
    print("Horário extraído pelo parser:")
    for dia, materias in schedule.items():
        print(f"{dia}: {materias}")

    if use_google_calendar:
        eventos_criados = generator.create_google_calendar_events(schedule, end_date)
        print(f"Eventos criados no Google Calendar: {eventos_criados}")
    else:
        ics_path = generator.generate_ics_calendar(schedule, end_date)
        print(f"Arquivo .ics gerado: {ics_path}")
    print("Dias encontrados:", horarios.keys())

if __name__ == "__main__":
    main()