from dataclasses import dataclass
from typing import Dict, List, Optional
import logging
from ..csp.solver import Solver
from ..csp.domain import Domain
from ..csp.variable import Variable, ResourceRequirements
from ..csp.constraints import ConstraintManager
from ..parser.level_parser import LevelParser
from .scheduler import LevelScheduler

@dataclass
class GeneratorResult:
    """Result of timetable generation"""
    success: bool
    timetable: Optional[Dict[int, List[Variable]]] = None
    error: Optional[str] = None
    stats: Optional[Dict] = None

class TimetableGenerator:
    """Generates complete timetables using CSP solver"""
    
    def __init__(self, db_path: str, levels_path: str):
        self.db_path = db_path
        self.levels_path = levels_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize components
        self.level_parser = LevelParser(db_path, levels_path)
        self.domain = Domain(db_path)
        self.constraint_manager = ConstraintManager(self.domain)
        self.solver = Solver(self.constraint_manager, self.domain)
        self.scheduler = LevelScheduler(self.domain)
    
    def _setup_logging(self):
        """Configure logging"""
        handler = logging.FileHandler('generator.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def generate(self, 
                max_attempts: int = 3, 
                timeout: float = 300) -> GeneratorResult:
        """Generate complete timetable for all levels"""
        try:
            # Load and validate level data
            self.level_parser.load_levels()
            validation_errors = self.level_parser.validate(raise_errors=False)
            if validation_errors:
                return GeneratorResult(
                    success=False,
                    error=f"Level validation failed: {validation_errors}"
                )
            
            # Generate timetable level by level
            complete_timetable = {}
            stats = {
                'attempts': 0,
                'total_variables': 0,
                'total_time': 0
            }
            
            for level, courses in self.level_parser.levels.items():
                level_num = int(level.split('_')[1])
                
                # Create variables for this level
                variables = self._create_variables(level_num, courses)
                stats['total_variables'] += len(variables)
                
                # Schedule this level
                result = self.scheduler.schedule_level(
                    level_num,
                    variables,
                    max_attempts
                )
                
                if not result.success:
                    return GeneratorResult(
                        success=False,
                        error=f"Failed to schedule level {level}: {result.error}"
                    )
                
                complete_timetable[level_num] = result.variables
                stats['attempts'] += max_attempts
            
            return GeneratorResult(
                success=True,
                timetable=complete_timetable,
                stats=stats
            )
            
        except Exception as e:
            self.logger.error(f"Generation failed: {str(e)}")
            return GeneratorResult(
                success=False,
                error=f"Generation failed: {str(e)}"
            )
    
    def _create_variables(self, 
                         level: int, 
                         courses: List[str]) -> List[Variable]:
        """Create CSP variables for courses"""
        variables = []
        
        for course in courses:
            # Get course requirements from database
            requirements = self._get_course_requirements(course)
            if requirements:
                var = Variable(course, level, requirements)
                # Set initial domain
                times, rooms, instructors = self.domain.get_available_values(
                    requirements
                )
                var.set_domain(times, rooms, instructors)
                variables.append(var)
        
        return variables
    
    def _get_course_requirements(self, 
                               course_id: str) -> Optional[ResourceRequirements]:
        """Get course requirements from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT course_type, min_capacity, requires_lab, requires_projector
                    FROM courses 
                    WHERE course_id = ?
                """, (course_id,))
                row = cur.fetchone()
                
                if row:
                    return ResourceRequirements(
                        room_type=row[0],
                        min_capacity=row[1],
                        requires_lab=bool(row[2]),
                        requires_projector=bool(row[3])
                    )
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {str(e)}")
            return None