#STUDENT NAME: Tomás Santos Fernandes
#STUDENT NUMBER: 112981

#DISCUSSED TPI-1 WITH: (names and numbers):
# Gabriel Santos, 113682
# João Gaspar, 114514
# Danilo Silva, 113384
# Source of help: GitHub, StackOverflow and several BlocksWorld Heuristic Problem resources on web

from tree_search import *
from strips import *
from blocksworld import *

class MyNode(SearchNode):

    def __init__(self, state, parent, cost, heuristic, depth, action=None):
        super().__init__(state, parent)
        self.depth = depth
        self.cost = cost 
        self.heuristic = heuristic
        self.action = action
        
    # Calculate A* cost of a node (use as property to avoid repeated calculations)
    @property
    def a_cost(self):
        return self.cost + self.heuristic 

class MyTree(SearchTree):

    def __init__(self, problem, strategy='breadth', improve=False):
        super().__init__(problem, strategy)
        self.num_open = len(self.open_nodes)
        self.num_solution = 0
        self.num_skipped = 0
        self.num_closed = 0
        self.improve = improve
        # A* cost of the root node, to avoid repeated heuristic() calls
        self.root_a_cost = self.problem.domain.heuristic(self.problem.initial, self.problem.goal)

    def astar_sorting_key(self, node):
        return (node.cost + node.heuristic, node.depth, str(node.state))

    def informeddepth_sorting_key(self, node):
        return (node.cost + node.heuristic, str(node.state))

    def astar_add_to_open(self, new_nodes_list):
        self.open_nodes.extend(new_nodes_list)
        # Sort open nodes by A* cost, then depth, then state by ascending order
        self.open_nodes.sort(key=lambda node: self.astar_sorting_key(node))

    def informeddepth_add_to_open(self, new_nodes_list):
        # Sort new nodes by A* cost, then state by ascending order
        new_nodes_list.sort(key=lambda node: self.informeddepth_sorting_key(node))
        # [:0] -> insert at the beginning of the list
        self.open_nodes[:0] = new_nodes_list 

    def search2(self, limit=None):  
        while self.open_nodes != []:
            node = self.open_nodes.pop(0)
            self.num_open -= 1  # Since I am removing it from the queue
            
            # If node is not a MyNode, convert it to MyNode (root)
            if not isinstance(node, MyNode):
                node = MyNode(node.state, node.parent, 0, self.root_a_cost, 0, None)
            
            node_a_cost = node.a_cost
            
            if self.problem.goal_test(node.state):
                self.num_solution += 1
                # Update/Set solution if no solution yet exists or if 'improve' is true 
                if not self.solution or (self.improve and node.cost < self.solution.cost):
                    self.solution = node
                # Return path if not looking for multiple solutions
                if not self.improve:
                    return self.get_path(node)
            
            # For depth search with limit
            if limit and node.depth >= limit:
                self.num_skipped += 1
                continue
            
            # To prevent exhaustive search, verify if A* cost is higher than the current solution cost
            if self.improve and self.solution:
                current_solution_cost = self.solution.a_cost if self.solution.parent else self.root_a_cost
                if node_a_cost >= current_solution_cost:
                    # Skip nodes with higher cost than the current solution, not counting with solution nodes 
                    if not self.problem.goal_test(node.state):
                        self.num_skipped += 1
                    continue
    
            # Only here increment closed nodes (because I am going to expand the current node that was removed from the queue)
            self.num_closed += 1
            new_nodes_list = []
            for action in self.problem.domain.actions(node.state):
                newstate = self.problem.domain.result(node.state, action)
                
                if newstate not in self.get_path(node):
                    cost = (node.cost if node.parent else 0) + self.problem.domain.cost(node.state, action) # Accumulate cost for new node
                    depth = (node.depth + 1) if node.state != self.problem.initial else (0 + 1)             # If node is root, depth is 0
                    heuristic = self.problem.domain.heuristic(newstate, self.problem.goal)
                    
                    newnode = MyNode(newstate, node, cost, heuristic, depth, action)
                    
                    new_nodes_list.append(newnode)
                    self.num_open += 1  # One more node to add to the open nodes queue
                           
            self.add_to_open(new_nodes_list)
        return self.get_path(self.solution) if self.solution else None # Get the path to the improved solution, or None if no solution was found
 
    def check_admissible(self, node):
        if node.parent is None:
            return True
        # Assume the given "node" is a solution node
        return self.check_admissible_rec(node, node.cost)

    def check_admissible_rec(self, node, total_cost):
        if node.parent is None: # Check admissibility for root node
            return self.root_a_cost <= total_cost
        # (total_cost - node.cost) is the actual cost of the path from the current node to the goal
        return node.heuristic <= (total_cost - node.cost) and self.check_admissible_rec(node.parent, total_cost)

    def get_plan(self, node):
        if node.parent == None:
            return []
        plan = self.get_plan(node.parent)
        plan += [node.action]
        return plan


class MyBlocksWorld(STRIPS):
    
    def heuristic(self, current_state, target_state):
        weights = {
            'stack': 1,
            'floor': 2,
            'blocking': 3
        }
        
        penalty_for_blocking = self.compute_blocking_penalty(current_state, target_state)
        penalty_for_floor = self.compute_floor_penalty(current_state, target_state)
        penalty_for_stack = self.compute_stack_penalty(current_state, target_state)

        # Combine the penalties with their respective weights
        return (penalty_for_stack * weights['stack']) + (penalty_for_floor * weights['floor']) + (penalty_for_blocking * weights['blocking'])

    def compute_blocking_penalty(self, current_state, target_state):
        total_blocking_penalty = 0
        # Dictionary with the current positions of the blocks {block: predicate}
        current_positions = {pred.args[0]: pred for pred in current_state if isinstance(pred, (On, Floor))}
        
        for target_predicate in target_state:
            if isinstance(target_predicate, On):
                block_to_check, block_below_goal = target_predicate.args
                # Skip penalty for blocks already on the floor
                if block_to_check in current_positions and isinstance(current_positions[block_to_check], Floor):
                    continue 
                
                # Add the number of blocks on top of the block_to_check 
                total_blocking_penalty += self.count_blocks_on_top(current_state, block_to_check, block_below_goal)

        return total_blocking_penalty

    def compute_floor_penalty(self, current_state, target_state):
        target_positions = {pred.args[0]: pred for pred in target_state if isinstance(pred, (On, Floor))}
        # Count the number of blocks on the floor that are not on the floor in the target state 
        floor_penalty_count = sum(1 for state_predicate in current_state
                                        if isinstance(state_predicate, Floor) and state_predicate.args[0] in target_positions 
                                                                                and isinstance(target_positions[state_predicate.args[0]], On))
        return floor_penalty_count

    def compute_stack_penalty(self, current_state, target_state):
        # Count the number of blocks that are not in the correct place in the target state
        misplaced_stack_count = sum(1 for state_predicate in current_state
                                        if isinstance(state_predicate, On) and state_predicate not in target_state)
        return misplaced_stack_count

    def count_blocks_on_top(self, current_state, block, block_below):
        return sum(1 for state_predicate in current_state
                        if isinstance(state_predicate, On) and 
                        state_predicate.args[1] == block_below and 
                        state_predicate.args[0] != block)