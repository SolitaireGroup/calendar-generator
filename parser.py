import pytesseract
from PIL import Image
import re
from typing import Dict, List, Optional
import logging

class ScheduleParser:
    """
    Parser para extrair horários escolares de imagens usando OCR
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurações padrão
        self.aulas_por_dia = 5
        self.horario_inicio = "07:30"
        self.horario_fim = "11:30"
        self.recreio_inicio = "09:45"
        self.recreio_fim = "10:00"
        
        # Padrões para reconhecer dias da semana
        self.dias_semana = {
            'segunda': ['segunda', 'seg', 'monday', 'mon'],
            'terca': ['terça', 'terca', 'ter', 'tuesday', 'tue'],
            'quarta': ['quarta', 'qua', 'wednesday', 'wed'],
            'quinta': ['quinta', 'qui', 'thursday', 'thu'],
            'sexta': ['sexta', 'sex', 'friday', 'fri']
        }
        
        # Padrões para reconhecer matérias comuns
        self.materias_comuns = [
            'matemática', 'matematica', 'math', 'mat',
            'português', 'portugues', 'portuguese', 'port',
            'história', 'historia', 'history', 'hist',
            'geografia', 'geography', 'geo',
            'química', 'quimica', 'chemistry', 'quim',
            'física', 'fisica', 'physics', 'fis',
            'biologia', 'biology', 'bio',
            'inglês', 'ingles', 'english', 'ing',
            'educação física', 'educacao fisica', 'ed. física', 'ed fisica',
            'arte', 'art',
            'filosofia', 'philosophy', 'filos',
            'sociologia', 'sociology', 'socio',
            'recreio', 'intervalo', 'break'
        ]
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extrai texto da imagem usando OCR
        """
        try:
            # Carrega a imagem
            image = Image.open(image_path)
            
            # Configurações do OCR para melhorar a precisão
            custom_config = r'--oem 3 --psm 6'
            
            # Extrai o texto
            text = pytesseract.image_to_string(image, config=custom_config, lang='por')
            
            self.logger.info(f"Texto extraído da imagem: {len(text)} caracteres")
            return text
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair texto da imagem: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """
        Limpa e normaliza o texto extraído
        """
        # Remove quebras de linha excessivas
        text = re.sub(r'\n+', '\n', text)
        
        # Remove espaços excessivos
        text = re.sub(r' +', ' ', text)
        
        # Converte para minúsculas para facilitar o parsing
        text = text.lower().strip()
        
        return text
    
    def identify_days(self, text: str) -> Dict[str, int]:
        dias = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA"]
        indices = {}
        for dia in dias:
            idx = text.upper().find(dia)
            if idx != -1:
                indices[dia.lower()] = idx
        # Se não encontrar, tente por linhas
        if not indices:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                for dia in dias:
                    if dia in line.upper():
                        indices[dia.lower()] = i
        return indices
    
    def extract_subjects_for_day(self, text: str, day_start: int, day_end: int) -> List[str]:
        """
        Extrai as matérias para um dia específico
        """
        day_text = text[day_start:day_end] if day_end else text[day_start:]
        
        subjects = []
        lines = day_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Procura por matérias conhecidas
            found_subject = None
            for materia in self.materias_comuns:
                if materia in line.lower():
                    found_subject = materia
                    break
            
            if found_subject:
                # Normaliza o nome da matéria
                normalized_subject = self.normalize_subject_name(found_subject)
                subjects.append(normalized_subject)
            else:
                # Se não encontrou uma matéria conhecida, tenta extrair palavras
                words = line.split()
                if words:
                    # Pega a primeira palavra como possível matéria
                    subjects.append(words[0].title())
        
        return subjects
    
    def normalize_subject_name(self, subject: str) -> str:
        """
        Normaliza o nome da matéria para um formato padrão
        """
        subject = subject.lower().strip()
        
        # Mapeamento de normalização
        normalization_map = {
            'matemática': 'Matemática',
            'matematica': 'Matemática',
            'português': 'Português',
            'portugues': 'Português',
            'história': 'História',
            'historia': 'História',
            'geografia': 'Geografia',
            'química': 'Química',
            'quimica': 'Química',
            'física': 'Física',
            'fisica': 'Física',
            'biologia': 'Biologia',
            'inglês': 'Inglês',
            'ingles': 'Inglês',
            'educação física': 'Educação Física',
            'educacao fisica': 'Educação Física',
            'ed. física': 'Educação Física',
            'ed fisica': 'Educação Física',
            'arte': 'Arte',
            'filosofia': 'Filosofia',
            'sociologia': 'Sociologia',
            'recreio': 'Recreio',
            'intervalo': 'Recreio'
        }
        
        return normalization_map.get(subject, subject.title())
    
    def parse_schedule(self, image_path: str) -> Dict[str, List[str]]:
        """
        Função principal que faz o parsing completo do horário
        """
        raw_text = self.extract_text_from_image(image_path)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        dias = ["segunda", "terça", "quarta", "quinta", "sexta"]
        horarios = {}
        # Pula a primeira linha se não for matéria
        start_idx = 0
        if not any(dia in lines[0].lower() for dia in dias):
            start_idx = 1
        for i, dia in enumerate(dias):
            materias = lines[start_idx + i*5 : start_idx + (i+1)*5]
            # Se faltar matéria, preenche com "???"
            while len(materias) < 5:
                materias.append("???")
            horarios[dia] = materias
        return horarios
    
    def parse_schedule_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Mesma lógica do parse_schedule, mas recebe texto direto
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        dias = ["segunda", "terça", "quarta", "quinta", "sexta"]
        horarios = {}
        # Pula a primeira linha se não for matéria
        start_idx = 0
        if not any(dia in lines[0].lower() for dia in dias):
            start_idx = 1
        for i, dia in enumerate(dias):
            materias = lines[start_idx + i*5 : start_idx + (i+1)*5]
            # Se faltar matéria, preenche com "???"
            while len(materias) < 5:
                materias.append("???")
            horarios[dia] = materias
        return horarios
    
    def get_time_slots(self) -> List[str]:
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
    
    def process_schedule(self, schedule: Dict[str, List[str]]) -> Dict[int, Dict[str, Optional[str]]]:
        """
        Processa o horário extraído e o organiza em um dicionário estruturado
        """
        resultado = {}
        
        # Dias da semana em português
        dias = ["segunda", "terça", "quarta", "quinta", "sexta"]
        
        # Itera sobre os dias e matérias no horário
        for dia, materias in schedule.items():
            if dia not in dias:
                continue
            dia_padrao = "terca" if dia in ["terca", "terça"] else dia
            weekday_num = ["segunda", "terca", "quarta", "quinta", "sexta"].index(dia_padrao)
            
            for aula_num, materia in enumerate(materias):
                # Cria uma entrada para cada aula
                if weekday_num not in resultado:
                    resultado[weekday_num] = {i: None for i in range(1, self.aulas_por_dia + 1)}
                
                # Adiciona a matéria à hora correspondente
                resultado[weekday_num][aula_num + 1] = materia if materia != "???" else None
        

        return resultado
