from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass
import time
from .variable import Variable, TimeSlot
from .domain import Domain
from .constraints import ConstraintManager, ConstraintViolation
from .optimization import SolutionOptimizer, OptimizationMetrics

@dataclass
class SolverStats:
    """Statistics about the solving process"""
    runtime: float
    backtracks: int
    assignments: int
    solutions_found: int
    best_score: float

class Solver:
    """CSP solver with optimization"""
    
    def __init__(self, 
                 constraint_manager: ConstraintManager,
                 domain: Domain,
                 max_runtime: float = 300):
        self.constraint_manager = constraint_manager
        self.domain = domain
        self.stats = SolverStats(0, 0, 0, 0, float('inf'))
        self.optimizer = SolutionOptimizer(max_runtime)
        self.best_solution: Optional[List[Variable]] = None
        self.best_metrics: Optional[OptimizationMetrics] = None
    
    def solve(self,
             variables: List[Variable],
             max_solutions: int = 1,
             timeout: float = 300) -> List[List[Variable]]:
        """Find optimized solutions"""
        start_time = time.time()
        solutions = []
        
        def backtrack(index: int) -> bool:
            if time.time() - start_time > timeout:
                return False
                
            if index == len(variables):
                # Score current solution
                metrics = self.optimizer.score_solution(variables)
                
                if (not self.best_metrics or 
                    metrics.total_score > self.best_metrics.total_score):
                    self.best_metrics = metrics
                    self.best_solution = [v.clone() for v in variables]
                    solutions.append(self.best_solution)
                    
                    # Early termination if solution is good enough
                    if (len(solutions) >= max_solutions and 
                        metrics.total_score > self.optimizer.best_score):
                        return True
                
                return len(solutions) < max_solutions
            
            # Order values by potential impact on optimization
            ordered_values = self._order_values(variables[index])
            
            for t, r, i in ordered_values:
                self.stats.assignments += 1
                
                # Try assignment
                variables[index].assign(t, r, i)  # Fixed: use variables[index] instead of variable
                
                # Check constraints
                violations = self.constraint_manager.check_assignment(
                    variables[:index + 1]
                )
                if not violations:
                    # Forward checking
                    if self._forward_check(variables[index + 1:]):
                        if backtrack(index + 1):
                            return True
                
                # Backtrack
                self.stats.backtracks += 1
                variables[index].unassign()  # Fixed: use variables[index]
                self._restore_domains(variables[index + 1:])
            
            return False
        
        backtrack(0)
        self.stats.runtime = time.time() - start_time
        return solutions
    
    def _forward_check(self, future_variables: List[Variable]) -> bool:
        """Apply forward checking to future variables"""
        for variable in future_variables:
            times, rooms, instructors = variable.get_domain()
            
            # Check if any values remain after constraint propagation
            if not (times and rooms and instructors):
                return False
                
            # Try to find at least one valid assignment
            valid_assignment = False
            for t in times:
                for r in rooms:
                    for i in instructors:
                        variable.assign(t, r, i)
                        if not self.constraint_manager.check_assignment([variable]):
                            valid_assignment = True
                            variable.unassign()
                            break
                    if valid_assignment:
                        break
                if valid_assignment:
                    break
                    
            variable.unassign()
            if not valid_assignment:
                return False
        
        return True
    
    def _restore_domains(self, variables: List[Variable]) -> None:
        """Restore original domains after backtracking"""
        for variable in variables:
            # Reset to full domain from Domain object
            times, rooms, instructors = self.domain.get_available_values(
                variable.requirements
            )
            variable.set_domain(times, rooms, instructors)
    
    def ac3(self, variables: List[Variable]) -> bool:
        """Apply AC-3 arc consistency algorithm"""
        arcs = [(i, j) for i in range(len(variables)) 
                      for j in range(len(variables)) if i != j]
        
        while arcs:
            i, j = arcs.pop(0)
            if self._revise(variables[i], variables[j]):
                if variables[i].domain_size() == 0:
                    return False
                    
                # Add neighboring arcs
                for k in range(len(variables)):
                    if k != i and k != j:
                        arcs.append((k, i))
        return True
    
    def _revise(self, var1: Variable, var2: Variable) -> bool:
        """Revise domain of var1 with respect to var2"""
        revised = False
        times1, rooms1, instructors1 = var1.get_domain()
        
        # Check each value in var1's domain
        for t1 in times1.copy():
            for r1 in rooms1.copy():
                for i1 in instructors1.copy():
                    # Try to find a compatible value in var2's domain
                    compatible = False
                    times2, rooms2, instructors2 = var2.get_domain()
                    
                    for t2 in times2:
                        for r2 in rooms2:
                            for i2 in instructors2:
                                var1.assign(t1, r1, i1)
                                var2.assign(t2, r2, i2)
                                
                                if not self.constraint_manager.check_assignment([var1, var2]):
                                    compatible = True
                                    break
                            if compatible:
                                break
                        if compatible:
                            break
                    
                    var1.unassign()
                    var2.unassign()
                    
                    if not compatible:
                        # Remove incompatible value
                        if t1 in times1:
                            times1.remove(t1)
                        if r1 in rooms1:
                            rooms1.remove(r1)
                        if i1 in instructors1:
                            instructors1.remove(i1)
                        revised = True
        
        return revised
    
    def _order_values(self, variable: Variable) -> List[tuple]:
        """Order domain values by potential optimization impact"""
        times, rooms, instructors = variable.get_domain()
        values = []
        
        for t in times:
            for r in rooms:
                for i in instructors:
                    # Calculate preliminary score
                    variable.assign(t, r, i)
                    score = self.optimizer.score_solution([variable]).total_score
                    variable.unassign()
                    values.append((score, (t, r, i)))
        
        # Sort by score in descending order
        values.sort(reverse=True)
        return [v[1] for v in values]