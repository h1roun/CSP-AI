from constraint import RecursiveBacktrackingSolver

class OptimizedSolver(RecursiveBacktrackingSolver):
    def __init__(self):
        super().__init__()
        self._variables = []
    
    def getSolution(self, domains, constraints, vconstraints):
        # Sort variables by MRV (Minimum Remaining Values)
        self._variables = sorted(
            domains.keys(),
            key=lambda var: (
                len(domains[var]),  # MRV
                -len(vconstraints.get(var, []))  # Degree heuristic as tiebreaker
            )
        )
        return super().getSolution(domains, constraints, vconstraints)
