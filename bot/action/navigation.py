"""
Physical Map & Pathfinding Navigation Module for PokeMMO
Implements coordinate-locked tracking, A* shortest-path finding, and collision recovery.
"""
import time
import random
import logging
from typing import List, Tuple, Dict, Set, Optional
from bot.action.input_engine import InputEngine

logger = logging.getLogger(__name__)

class MapNode:
    """Represents a single grid cell in the pathfinding matrix"""
    def __init__(self, x: int, y: int, parent=None):
        self.x = x
        self.y = y
        self.parent = parent
        
        self.g = 0  # Cost from start to current node
        self.h = 0  # Heuristic cost from current node to target
        self.f = 0  # Total cost (g + h)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


class OverworldMap:
    """Defines a map layout with grids, solid obstacles, and portals"""
    def __init__(self, name: str, width: int, height: int):
        self.name = name
        self.width = width
        self.height = height
        self.obstacles: Set[Tuple[int, int]] = set()
        self.grass_patches: Set[Tuple[int, int]] = set()
        # Teleport coordinates map: (x, y) -> (target_map, target_x, target_y)
        self.portals: Dict[Tuple[int, int], Tuple[str, int, int]] = {}

    def add_obstacle(self, x: int, y: int):
        self.obstacles.add((x, y))

    def add_obstacle_rect(self, x_start: int, y_start: int, x_end: int, y_end: int):
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                self.obstacles.add((x, y))

    def add_grass(self, x: int, y: int):
        self.grass_patches.add((x, y))

    def add_grass_rect(self, x_start: int, y_start: int, x_end: int, y_end: int):
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                self.grass_patches.add((x, y))

    def add_portal(self, x: int, y: int, target_map: str, target_x: int, target_y: int):
        self.portals[(x, y)] = (target_map, target_x, target_y)

    def is_walkable(self, x: int, y: int) -> bool:
        """Checks if a cell is within bounds and not blocked"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return (x, y) not in self.obstacles


class NavigationEngine:
    """Tracks position, calculates A* paths, and moves the avatar grid-by-grid"""
    def __init__(self, input_engine: InputEngine):
        self.input = input_engine
        
        # Grid-locking timings: in PokeMMO, holding a direction for ~0.25s walks exactly 1 tile
        self.step_duration = 0.25 
        
        # State tracking (Dead Reckoning)
        self.current_map = "PalletTown"
        self.x = 8
        self.y = 8
        
        # Active maps database
        self.maps: Dict[str, OverworldMap] = {}
        self._initialize_game_maps()

    def set_location(self, map_name: str, x: int, y: int):
        """Calibrates or resets coordinates"""
        self.current_map = map_name
        self.x = x
        self.y = y
        logger.info(f"📍 Navigation Calibrated to: {map_name} ({x}, {y})")

    def _initialize_game_maps(self):
        """Sets up default obstacle layouts for campaign regions (e.g. Kanto early routes)"""
        # 1. Pallet Town (width: 20, height: 20)
        pallet = OverworldMap("PalletTown", 20, 20)
        # Red's House (obstacle box)
        pallet.add_obstacle_rect(3, 3, 7, 6)
        # Blue's House (obstacle box)
        pallet.add_obstacle_rect(12, 3, 16, 6)
        # Oak's Lab (obstacle box)
        pallet.add_obstacle_rect(10, 11, 15, 15)
        # Fences and water border
        pallet.add_obstacle_rect(0, 0, 19, 1) # Top fence
        pallet.add_obstacle_rect(0, 0, 1, 19)  # Left border
        pallet.add_obstacle_rect(18, 0, 19, 19) # Right border
        # Portal to Route 1 (Top exit)
        pallet.add_portal(8, 1, "Route1", 8, 18)
        pallet.add_portal(9, 1, "Route1", 9, 18)
        self.maps["PalletTown"] = pallet

        # 2. Route 1 (width: 20, height: 20)
        r1 = OverworldMap("Route1", 20, 20)
        # Side trees and borders
        r1.add_obstacle_rect(0, 0, 2, 19)   # Left border
        r1.add_obstacle_rect(17, 0, 19, 19)  # Right border
        # Ledges (can only hop down, treating as solid obstacles for upward pathing)
        r1.add_obstacle_rect(5, 8, 12, 8)
        # Grass patches for farming
        r1.add_grass_rect(3, 4, 6, 7)
        r1.add_grass_rect(12, 12, 15, 15)
        # Portals
        r1.add_portal(8, 19, "PalletTown", 8, 2)
        r1.add_portal(9, 19, "PalletTown", 9, 2)
        r1.add_portal(8, 0, "ViridianCity", 8, 18)
        r1.add_portal(9, 0, "ViridianCity", 9, 18)
        self.maps["Route1"] = r1

    def a_star_pathfind(self, start: Tuple[int, int], end: Tuple[int, int], map_layout: OverworldMap) -> Optional[List[Tuple[int, int]]]:
        """Calculates shortest route using A* Algorithm"""
        start_node = MapNode(start[0], start[1])
        end_node = MapNode(end[0], end[1])

        open_list: Set[MapNode] = {start_node}
        closed_list: Set[MapNode] = set()

        while open_list:
            # Find node with lowest f cost
            current_node = min(open_list, key=lambda n: n.f)
            
            open_list.remove(current_node)
            closed_list.add(current_node)

            # Reached target?
            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append((current.x, current.y))
                    current = current.parent
                return path[::-1]  # Return reversed path

            # Generate neighbors (Up, Down, Left, Right)
            neighbors = [
                (0, -1, "up"),
                (0, 1, "down"),
                (-1, 0, "left"),
                (1, 0, "right")
            ]
            
            for nx, ny, _ in neighbors:
                px, py = current_node.x + nx, current_node.y + ny
                
                if not map_layout.is_walkable(px, py):
                    continue

                neighbor = MapNode(px, py, current_node)
                if neighbor in closed_list:
                    continue

                # Calculate f, g, h values
                neighbor.g = current_node.g + 1
                # Manhattan distance heuristic
                neighbor.h = abs(neighbor.x - end_node.x) + abs(neighbor.y - end_node.y)
                neighbor.f = neighbor.g + neighbor.h

                # Check if neighbor is already in open list with lower g cost
                existing_open = next((n for n in open_list if n == neighbor), None)
                if existing_open and neighbor.g >= existing_open.g:
                    continue

                open_list.add(neighbor)

        return None # No path found

    def take_step(self, direction: str) -> bool:
        """
        Executes a single step in a direction and updates coordinates.
        Includes random human-like micro-delays to satisfy anti-cheat detectors.
        """
        active_map = self.maps.get(self.current_map)
        if not active_map:
            logger.error(f"Cannot navigate: Unknown map {self.current_map}")
            return False

        dx, dy = 0, 0
        if direction == "up": dy = -1
        elif direction == "down": dy = 1
        elif direction == "left": dx = -1
        elif direction == "right": dx = 1

        target_x, target_y = self.x + dx, self.y + dy

        # Collision Check
        if not active_map.is_walkable(target_x, target_y):
            logger.warning(f"💥 Hit obstacle at ({target_x}, {target_y}) in {self.current_map}")
            self.handle_collision(direction)
            return False

        # Execute walk
        self.input.walk(direction, self.step_duration)
        
        # Dead reckoning update
        self.x = target_x
        self.y = target_y
        
        logger.info(f"🚶 Step {direction.upper()} to: ({self.x}, {self.y})")

        # Portal/Transition Check
        if (self.x, self.y) in active_map.portals:
            target_map, px, py = active_map.portals[(self.x, self.y)]
            logger.info(f"🌀 Portal transition! Moving from {self.current_map} to {target_map}")
            time.sleep(1.0)  # Wait for PokeMMO map loading transition screen
            self.current_map = target_map
            self.x = px
            self.y = py
            
        return True

    def navigate_to(self, target_x: int, target_y: int) -> bool:
        """Pathfinds and moves the character step-by-step to the destination coordinates"""
        active_map = self.maps.get(self.current_map)
        if not active_map:
            logger.error(f"Cannot pathfind: Layout of {self.current_map} not loaded.")
            return False

        logger.info(f"🚀 Pathfinding: ({self.x}, {self.y}) -> ({target_x}, {target_y})")
        path = self.a_star_pathfind((self.x, self.y), (target_x, target_y), active_map)

        if not path:
            logger.error("❌ Path finding failed: Destination unreachable.")
            return False

        logger.info(f"🧭 Shortest path calculated: {len(path)-1} nodes.")
        
        # Execute each node in path
        for i in range(1, len(path)):
            curr_node = path[i-1]
            next_node = path[i]
            
            # Determine direction
            dx = next_node[0] - curr_node[0]
            dy = next_node[1] - curr_node[1]
            
            direction = ""
            if dx == 1: direction = "right"
            elif dx == -1: direction = "left"
            elif dy == 1: direction = "down"
            elif dy == -1: direction = "up"
            
            if direction:
                success = self.take_step(direction)
                if not success:
                    # Re-plan path from current position if blocked
                    return self.navigate_to(target_x, target_y)
                
                # Sleep a short random duration between steps to mimic human pacing
                time.sleep(random.uniform(0.05, 0.15))

        logger.info("🎉 Target destination reached successfully!")
        return True

    def handle_collision(self, blocked_dir: str):
        """Self-correcting stuck recovery mechanism to bypass obstacles or player blocks"""
        logger.warning(f"⚠️ Stuck detection triggered for direction {blocked_dir}. Executing recovery...")
        # Step back in reverse direction
        reverse = {"up": "down", "down": "up", "left": "right", "right": "left"}
        rev_dir = reverse[blocked_dir]
        
        # Jiggle/Sidestep sequence to bypass collision block
        jiggle_dir = "right" if blocked_dir in ["up", "down"] else "down"
        
        self.input.walk(rev_dir, self.step_duration)
        time.sleep(0.2)
        self.input.walk(jiggle_dir, self.step_duration)
        time.sleep(0.2)
        
        logger.info("🔄 Stuck recovery finished. Pathfinding will recalculate grid coordinates.")

    def grind_grass(self, coord_a: Tuple[int, int], coord_b: Tuple[int, int], battles_to_run: int = 5):
        """Autonomously paces back and forth between two coordinates in grass to trigger farm battles"""
        logger.info(f"🌾 Starting grass farming grind between {coord_a} and {coord_b}...")
        
        # Navigate to starting spot
        self.navigate_to(coord_a[0], coord_a[1])
        
        runs = 0
        while runs < battles_to_run:
            # Alternately navigate between spot A and spot B
            target = coord_b if (self.x, self.y) == coord_a else coord_a
            self.navigate_to(target[0], target[1])
            time.sleep(0.5) # Sleep to let the overworld spawn trigger check
            
            # Note: The main loop will interrupt this loop if the Vision Engine detects get_game_state() == "BATTLE"
            # Here we provide a manual simulated counter for testing
            runs += 1

if __name__ == "__main__":
    input_eng = InputEngine()
    nav = NavigationEngine(input_eng)
    print("Navigation Engine & Map Matrix Initialized!")
    print(f"Current Position: {nav.current_map} ({nav.x}, {nav.y})")
