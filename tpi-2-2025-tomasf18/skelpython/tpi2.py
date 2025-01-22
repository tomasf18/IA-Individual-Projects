#encoding: utf8

# YOUR NAME: Tomás Santos Fernandes
# YOUR NUMBER: 112981

# COLLEAGUES WITH WHOM YOU DISCUSSED THIS ASSIGNMENT (names, numbers):
# - Gabriel Santos      | 113682
# - Pedro Pinto         | 115304

# Other sources:
# - https://www.cs.cornell.edu/courses/cs4700/2011fa/lectures/05_CSP.pdf -> For exercises 3 & 4

from itertools import product
from collections import Counter, deque, defaultdict
from semantic_network import *
from constraintsearch import *
from bayes_net import *


# ---------------------------------------------------------------------------------------------- #

# Exercise 1
class MySN(SemanticNetwork):

    def __init__(self):
        SemanticNetwork.__init__(self)
    
    # General query method, processing different types of relations according to their specificities
    def query(self,entity,relname):
        all_declarations = self.query_local(relname=relname)                                                    # All declarations in the semantic network that have relname as relation name
        definitive_type = Counter([type(d.relation).__name__ for d in all_declarations]).most_common(1)[0][0]   # Counts the the type of the relations and gets the most common one
        
        declarations = [] 
        
        # Member and Subtype relations -> Only the local ones are relevant
        if definitive_type in ['Member', 'Subtype']:
            # Get the local declarations of the entity with the relation name and the definitive type
            declarations = [d for d in self.query_local(e1=entity, relname=relname) if isinstance(d.relation, eval(definitive_type))]
            return [d.relation.entity2 for d in declarations]
        
        # AssocOne 
        if definitive_type == 'AssocOne':
            declarations = self.query_aux(entity, relname, AssocOne, cancel=True)
            most_common = Counter([d.relation.entity2 for d in declarations]).most_common(1)[0][0]
            return [most_common]
        
        # AssocNum
        if definitive_type == 'AssocNum':
            declarations = self.query_aux(entity, relname, AssocNum, cancel=True)
            total = sum(d.relation.entity2 for d in declarations if not isinstance(d.relation.entity2, str))
            n = len(declarations)
            return [total/n]
      
        # AssocSome
        if definitive_type == 'AssocSome':
            declarations = self.query_aux(entity, relname, AssocSome)
            return [element for element in set(d.relation.entity2 for d in declarations)] # Remove duplicates
        
        return declarations

    # Auxiliary method to query the semantic network recursively (with inheritance options -> either with cancel or not)
    def query_aux(self, entity, relname, rel_type, cancel=False):
        local_decl = [d for d in self.query_local(e1=entity, relname=relname) if isinstance(d.relation, rel_type)]               
        local_pred = [d.relation.entity2 for d in self.query_local(e1=entity) if isinstance(d.relation, Subtype) or isinstance(d.relation, Member)] 
        
        if cancel:
            local_assocs = [d.relation.name for d in local_decl]
            for predecessor in local_pred:
                local_decl.extend(d for d in self.query_aux(predecessor, relname, rel_type, True) if d.relation.name not in local_assocs)
        else:
            for predecessor in local_pred:
                local_decl.extend(d for d in self.query_aux(predecessor, relname, rel_type, False))
                
        return set(local_decl)
            
            
# ---------------------------------------------------------------------------------------------- #
          
# Exercise 2 
class MyBN(BayesNet):

    def __init__(self):
        BayesNet.__init__(self)
    
    def test_independence(self, v1, v2, given):
        """ Test the independence between two variables given a set of variables """
        
        # Build the graph
        graph = self.build_graph(v1, v2, given)

        # Remove edges involving the given variables
        self.remove_given_edges(graph, given)

        # Convert the graph to an edge list
        edge_list = self.convert_to_edge_list(graph)

        # Check for independence
        independent = not self.exists_path_connecting_the_variables(graph, v1, v2)

        return edge_list, independent

    def build_graph(self, v1, v2, given):
        """ Build the undirected graph recursively """
        
        graph = defaultdict(set)
        visited_variable_in_path = set()
        
        self._build_graph_recursive(graph, visited_variable_in_path, set([v1, v2] + given))
        
        self.add_mother_edges(graph, visited_variable_in_path)
        
        return graph

    # Auxiliary method to build the graph
    def _build_graph_recursive(self, graph: dict, visited_variable_in_path, to_process):
        if not to_process:                              # Base case: no more variables to process
            return
        
        var = to_process.pop()              
        
        if var in visited_variable_in_path:             # Base case: variable already visited
            return
        
        visited_variable_in_path.add(var)               # Mark the variable as visited
            
        # Getting all the mothers of the variable, create the edges and add the mothers to the to_process set, so that it can go to the all the ancestors of the variable 
        # (until the ancestor has no mother)
        for (mtrue, mfalse, _) in self.dependencies.get(var, []):   
            for mother in mtrue + mfalse:
                # Add the edge between the variable and the mother (set default in case the variable is not in the graph yet, if it is, add the mother to the set of neighbors)
                graph.setdefault(var, set()).add(mother)
                graph.setdefault(mother, set()).add(var)
                if mother not in visited_variable_in_path:
                    to_process.add(mother)
                    
        self._build_graph_recursive(graph, visited_variable_in_path, to_process)

    def add_mother_edges(self, graph: dict, visited_variable_in_path):
        """ Add edges between all pairs of mother variables recursively """
        def add_edges(mothers):
            if not mothers:
                return
            mother1 = mothers.pop()
            for mother2 in mothers:
                graph.setdefault(mother1, set()).add(mother2)
                graph.setdefault(mother2, set()).add(mother1)
            add_edges(mothers)

        # For each variable, get all the mothers and add the edges between them (all pairs)
        for var in visited_variable_in_path:    
            mothers = set()
            for (mtrue, mfalse, _) in self.dependencies.get(var, []):
                mothers.update(mtrue + mfalse)
            add_edges(list(mothers))
    
    def remove_given_edges(self, graph, given):
        """Remove edges involving any of the given variables recursively"""
        if not given:
            return
        given_var = given.pop()
        if given_var in graph:
            for neighbor in list(graph[given_var]):
                graph[neighbor].remove(given_var)
            del graph[given_var]
        self.remove_given_edges(graph, given)
                
    def convert_to_edge_list(self, graph):
        """Convert the graph to a list of edges"""
        return [element for element in set((node, neighbor) for node in graph for neighbor in graph[node] if node < neighbor)] # Only add the edge once, distinguishing the order of the nodes
    
    def exists_path_connecting_the_variables(self, graph, source, target):
        """Check if a path exists between source and target using BFS algorithm"""
        queue = deque([source])
        visited = set()
        while queue:
            current = queue.popleft()                   # Get the first element of the queue, while removing it
            if current == target:
                return True
            if current not in visited:
                visited.add(current)
                queue.extend(graph[current] - visited)  # Add, as Breadth-First Search (to the final), the new neighbors of the current node that haven't been visited yet
        return False


# ---------------------------------------------------------------------------------------------- #

# Exercise 3
class MyCS(ConstraintSearch):

    def __init__(self,domains,constraints):
        ConstraintSearch.__init__(self,domains,constraints)
    
    def search_all(self, domains: dict = None):
        if domains == None:
            # Domains: Dictionary composed by all variables and their respective possible values
            domains = self.domains  
            
        # Base cases
        if any([variable_list_values == [] for variable_list_values in domains.values()]):
            return []

        if all([len(variable_list_values) == 1 for variable_list_values in list(domains.values())]):
            return [{ v:variable_list_values[0] for (v,variable_list_values) in domains.items() }] 
        # ---

        solutions = self.expand(domains)
        
        # Remove duplicated solutions
        solutions_without_rep = []
        visited = set() 
        for solution in solutions:
            solution_tuple = tuple(sorted(solution.items())) # Ordet by variable name so that there is no other tuple with the same values (but in different order)
            if solution_tuple not in visited:
                solutions_without_rep.append(solution)
                visited.add(solution_tuple)
        
        return solutions_without_rep
    
    def expand(self, domains):
        solutions = []
        # Heuristic: Choose the variable with the smallest domain
        var = min((v for v in domains if len(domains[v]) > 1), key=lambda v: len(domains[v]))
        # For each value of the chosen variable, create a new domain and propagate the restrictions implied by this assignment to other variables
        for value in domains[var]:
            new_variables_domains = dict(domains)               # Copy the current domains
            new_variables_domains[var] = [value]                # Choose a value for the variable

            self.propagate(new_variables_domains, var)          # Based on the chosen value, propagate the restrictions to the other variables
            
            solutions += self.search_all(new_variables_domains)
            
        return solutions
    

# ---------------------------------------------------------------------------------------------- #
    
# Exercise 4
def handle_ho_constraint(domains, constraints, variables, constraint):
    extra = {}
    
    # Create the auxiliary variable name
    aux_var = ''.join(variables)
    
    # Generate the domain for the auxiliary variable based on the higher-order constraint (domain = cartesian product of the domains of the original variables)
    domains[aux_var] = [tuple(values) for values in product(*[domains[v] for v in variables]) if constraint(values)]
    
    # Add binary constraints between the auxiliary variable and the original variables
    for i, var in enumerate(variables):
        extra[(aux_var, var)] = lambda vt, xt, v, x, i=i: xt[i] == x
    
    # Add the new constraints
    constraints |= extra
    
    # Invert the variables order and create new constraints adapted to the new order
    def invert_constraint_args_order(constraints, entry):
        return lambda w2, x2, w1, x1:constraints[entry](w1,x1,w2,x2)

    # Add the inverted constraints
    constraints |= { (v2, v1): invert_constraint_args_order(extra, (v1, v2)) for v1, v2 in extra }
        