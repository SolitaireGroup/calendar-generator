import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
import logging
from ics import Calendar, Event
from parser import ScheduleParser
from google_calendar_manager import GoogleCalendarManager

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CalendarGenerator:
    """
    Gerador de calendário a partir de horários escolares
    """
    
    def __init__(self, use_google_calendar: bool = False, turno: str = "manha"):
        self.parser = ScheduleParser(turno=turno)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.use_google_calendar = use_google_calendar
        self.google_manager = GoogleCalendarManager() if use_google_calendar else None
    
    def process_text(self, text: str, end_date: str) -> str:
        """
        Processa um texto de horário e gera o arquivo .ics ou eventos no Google Calendar
        """
        try:
            logger.info(f"Processando texto")
            
            # Faz o parsing do horário
            schedule = self.parser.parse_schedule_from_text(text)
            logger.info(f"Horário extraído: {schedule}")
            
            if self.use_google_calendar:
                # Cria eventos diretamente no Google Calendar
                self.create_google_calendar_events(schedule, end_date)
                return "Google Calendar atualizado com sucesso!"
            else:
                # Gera arquivo .ics
                ics_file = self.create_ics_file(schedule, end_date)
                return ics_file
            
        except Exception as e:
            logger.error(f"Erro ao processar texto: {e}")
            raise

    def create_google_calendar_events(self, schedule: dict, end_date: str):
        """
        Cria os eventos no Google Calendar
        """
        if not self.google_manager:
            raise ValueError("Google Calendar Manager não está inicializado.")
        
        self.google_manager.authenticate()
        
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        today = date.today()
        dias = ["segunda", "terça", "quarta", "quinta", "sexta"]
        
        for dia_nome, materias in schedule.items():
            if dia_nome not in dias:
                continue

            weekday_num = dias.index(dia_nome)
            
            for i, materia in enumerate(materias):
                if not materia or materia.lower() == "recreio":
                    continue
                
                # Pega os horários da aula
                time_slots = self.parser.get_time_slots()
                start_time_str, end_time_str = time_slots[i].split('-')
                
                # Encontra a primeira ocorrência do dia da semana a partir de hoje
                current_day = today
                days_ahead = weekday_num - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                current_day += timedelta(days=days_ahead)
                
                start_datetime = datetime.combine(
                    current_day,
                    datetime.strptime(start_time_str, "%H:%M").time()
                )
                
                end_datetime = datetime.combine(
                    current_day,
                    datetime.strptime(end_time_str, "%H:%M").time()
                )
                
                # Cria o evento com os argumentos corretos
                self.google_manager.create_event(
                    title=materia,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    dia_semana=dia_nome,
                    recurrence=[f"RRULE:FREQ=WEEKLY;UNTIL={end_dt.strftime('%Y%m%d')}T235959Z"]
                )
    
    def create_ics_file(self, schedule: dict, end_date: str) -> str:
        """
        Cria um arquivo .ics com os eventos do calendário
        """
        c = Calendar()
        
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        today = date.today()
        dias = ["segunda", "terça", "quarta", "quinta", "sexta"]

        for dia_nome, materias in schedule.items():
            if dia_nome not in dias:
                continue

            weekday_num = dias.index(dia_nome)
            
            for i, materia in enumerate(materias):
                if not materia or materia.lower() == "recreio":
                    continue
                
                time_slots = self.parser.get_time_slots()
                start_time_str, end_time_str = time_slots[i].split('-')
                
                current_day = today
                days_ahead = weekday_num - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                current_day += timedelta(days=days_ahead)

                start_datetime = datetime.combine(
                    current_day,
                    datetime.strptime(start_time_str, "%H:%M").time()
                )
                
                end_datetime = datetime.combine(
                    current_day,
                    datetime.strptime(end_time_str, "%H:%M").time()
                )
                
                event = Event()
                event.name = materia
                event.begin = start_datetime.isoformat()
                event.end = end_datetime.isoformat()
                
                # Adiciona regra de recorrência
                event.add('RRULE', f'FREQ=WEEKLY;UNTIL={end_dt.strftime("%Y%m%d")}T235959Z')
                
                c.events.add(event)
        
        filename = f"calendario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ics"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(c.serialize_iter())
            
        return str(filepath)

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
    
    try:
        if use_google_calendar:
            generator.process_image_and_create_events(image_path, end_date)
            print("Eventos criados no Google Calendar!")
        else:
            ics_path = generator.process_image_and_create_ics(image_path, end_date)
            print(f"Arquivo .ics gerado: {ics_path}")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
