import numpy as np
import networkx as nx
import json
import copy

class Cube:
    def __init__(self):
        # The PIECES are counted from Left-to-Right(axis=2), Top-to-Bottom (axis=1), and Front-to-Back (axis=0), in that order. The fourteenth piece is the invisible and irrelevant center-most piece of the cube
        self.piece_initial_positions = np.array([
            [[1 , 2 , 3 ], [4 , 5 , 6 ], [7 , 8 , 9 ]],
            [[10, 11, 12], [13, 14, 15], [16, 17, 18]],
            [[19, 20, 21], [22, 23, 24], [25, 26, 27]]
        ])

        # This is the intial state of the cube, which is the solved state
        # Notice that only the corners are marked by 'xyz', and only the edges are marked by 'g' ('g' for good, other possible value is 'b' for bad)
        # Here x stands for the x-axis, y for y-axis and z for z-axis. The string means that the piece's axes are aligned with x, y and z axes of the cube in that order
        # g stands for "good", which is one of the two possible orientations of an edge piece at any given position, and other one is b, which stands for "bad"
        # The center pieces are not marked, as they always remain the same

        self.piece_initial_orientations = np.array([
            [['xyz', 'g', 'xyz'], ['g', 'F', 'g'], ['xyz', 'g', 'xyz']],
            [['g', 'U', 'g'], ['L', 'C', 'R'], ['g', 'D', 'g']],
            [['xyz', 'g', 'xyz'], ['g', 'B', 'g'], ['xyz', 'g', 'xyz']],
        ])

        # Define positions for edges and corners
        self.piece_current_positions = copy.deepcopy(self.piece_initial_positions)
        self.piece_current_orientations = copy.deepcopy(self.piece_initial_orientations)

        # Call the piece-categorizing methods and store them           
        self.edge_positions, self.corner_positions = self.categorize_positions_over_piece_types()
        self.edge_ids, self.corner_ids = self.categorize_ids_over_piece_types()

        # Sort positions and ids for consistent ordering
        self.edge_positions.sort()
        self.corner_positions.sort()
        self.edge_ids.sort()
        self.corner_ids.sort()

        self.move_map = {
            'U': self._U, 'F': self._F, 'B': self._B, 'D': self._D, 'L': self._L, 'R': self._R,
            'u': self._u, 'f': self._f, 'b': self._b, 'd': self._d, 'l': self._l, 'r': self._r,
            'M': self._M, 'E': self._E, 'S': self._S, 'm': self._m, 'e': self._e, 's': self._s,
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

        self.corner_piece_move_vs_orientation_map = {
            'U': lambda s: s[1] + s[0] + s[2],
            'u': lambda s: s[1] + s[0] + s[2],
            'D': lambda s: s[1] + s[0] + s[2],
            'd': lambda s: s[1] + s[0] + s[2],
            'L': lambda s: s[0] + s[2] + s[1],
            'l': lambda s: s[0] + s[2] + s[1],
            'R': lambda s: s[0] + s[2] + s[1],
            'r': lambda s: s[0] + s[2] + s[1],
            'F': lambda s: s[2] + s[1] + s[0],
            'f': lambda s: s[2] + s[1] + s[0],
            'B': lambda s: s[2] + s[1] + s[0],
            'b': lambda s: s[2] + s[1] + s[0],
        }
        self.tables = self._load_tables_from_json([
            'corner_position_distance_table.json',
            'edge_position_distance_table.json',
            'position_movement_table.json'
        ])
        self.edge_distances = self.tables["edge_distances"]
        self.corner_distances = self.tables["corner_distances"]
        self.movements = self.tables["movements"]

    def categorize_ids_over_piece_types(self):
        """Identifies edge and corner pieces based on orientation markers."""
        edge_ids = []
        corner_ids = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = self.piece_initial_positions[i, j, k]
                    orientation = self.piece_initial_orientations[i, j, k]
                    if orientation == 'g':  # corner
                        edge_ids.append(piece_id)
                    else:
                        corner_ids.append(piece_id)
        return edge_ids, corner_ids
    
    def categorize_positions_over_piece_types(self):
        """ Iterate through all positions in the cube and sort their positions into edges and corners """
        edge_positions = []
        corner_positions = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_positions[i, j, k] in [5, 11, 13, 14, 15, 17, 23]:
                        continue
                    else:
                        if self.piece_current_orientations[i, j, k] != 'g':
                            corner_positions.append((i, j, k))
                        else:
                            edge_positions.append((i, j, k))
        return edge_positions, corner_positions

    def _load_tables_from_json(self, filenames: list):
        """
        Loads precomputed tables from JSON files and returns them in a dictionary.

        Args:
            filenames: List of JSON filenames containing the precomputed tables

        Returns:
            dict: A dictionary containing loaded tables, with keys:
                "edge_distances", "corner_distances", "movements".
                Values are the loaded tables, or None if loading failed for a table type.
        """
        tables = {
            "edge_distances": None,
            "corner_distances": None,
            "movements": None
        }
        
        for filename in filenames:
            try:
                with open(filename, 'r') as f:
                    serializable_table = json.load(f)
                    
                    # Determine which table type this file contains
                    if 'edge' in filename.lower() and 'distance' in filename.lower():
                        tables["edge_distances"] = {}
                        for pair_str, distance in serializable_table.items():
                            pos_tuple = tuple(eval(pair_str))  # Consistent parsing using eval
                            tables["edge_distances"][pos_tuple] = distance
                            
                    elif 'corner' in filename.lower() and 'distance' in filename.lower():
                        tables["corner_distances"] = {}
                        for pair_str, distance in serializable_table.items():
                            pos_tuple = tuple(eval(pair_str))  # Consistent parsing
                            tables["corner_distances"][pos_tuple] = distance
                            
                    elif 'position' in filename.lower() and 'movement' in filename.lower():
                        tables["movements"] = {}
                        for move, position_movements in serializable_table.items():
                            movements = {}
                            for from_pos_str, to_pos_str in position_movements.items():
                                from_pos = tuple(eval(from_pos_str))
                                to_pos = tuple(eval(to_pos_str))
                                movements[from_pos] = to_pos
                            tables["movements"][move] = movements
                            
            except FileNotFoundError:
                print(f"FileNotFoundError: '{filename}' not found.")
            except json.JSONDecodeError:
                print(f"JSONDecodeError: Could not decode JSON from '{filename}'. File may be corrupted.")
            except Exception as e:
                print(f"Error loading '{filename}': {e}")
        
        # Log which tables were successfully loaded
        loaded_tables = [key for key, value in tables.items() if value is not None]
        if loaded_tables:
            print(f"Successfully loaded tables: {', '.join(loaded_tables)}")
        else:
            print("Warning: No tables were successfully loaded")
            
        return tables
    
    def _rotate_slice(self, perspective, slice_idx, direction):
        """ Rotate a face (0=front, 1=middle, 2=back) seen from the given perspective (0=front, 1=top, 2=left) in the given direction """
        def change_perspective(cube, perspective, direction):
            if perspective == 0: return cube
            else: return np.rot90(cube, k=direction, axes=(0, perspective))
        # Convert to the desired perspective, rotate the slice, then convert back
        self.piece_current_positions = change_perspective(self.piece_current_positions, perspective, -1)
        self.piece_current_positions[slice_idx] = np.rot90(self.piece_current_positions[slice_idx], k=direction, axes=(0, 1))
        self.piece_current_positions = change_perspective(self.piece_current_positions, perspective, 1)

        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, -1)
        self.piece_current_orientations[slice_idx] = np.rot90(self.piece_current_orientations[slice_idx], k=direction, axes=(0, 1))
        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, 1)

    def _update_edge_orientations(self, move):
        """ Update the orientations of edges based on the move made """
        for edge in self.edge_positions:
            if edge in self.movements[move].keys():
                piece_id = self.piece_current_positions[edge]
                piece_initial_position = list(zip(*np.where(self.piece_initial_positions == piece_id)))[0]
                if self.edge_distances[(piece_initial_position, edge)] == self.edge_distances[(piece_initial_position, self.movements[move][edge])]:
                    next_orientation = ['g', 'b']
                    next_orientation.remove(self.piece_current_orientations[edge])
                    self.piece_current_orientations[edge] = next_orientation[0]
    
    def _update_corner_orientations(self, move):
        """ Update the orientations of corners based on the move made """
        for corner in self.corner_positions:
            if corner in self.movements[move].keys():
                current_orientation = self.piece_current_orientations[corner]
                self.piece_current_orientations[corner] = self.corner_piece_move_vs_orientation_map[move](current_orientation)

    def _F(self): self._rotate_slice(perspective=0, slice_idx=0, direction=-1)
    def _f(self): self._rotate_slice(perspective=0, slice_idx=0, direction=1)
    def _M(self): self._rotate_slice(perspective=0, slice_idx=1, direction=-1)
    def _m(self): self._rotate_slice(perspective=0, slice_idx=1, direction=1)
    def _B(self): self._rotate_slice(perspective=0, slice_idx=2, direction=1)
    def _b(self): self._rotate_slice(perspective=0, slice_idx=2, direction=-1)

    def _U(self): self._rotate_slice(perspective=1, slice_idx=0, direction=-1)
    def _u(self): self._rotate_slice(perspective=1, slice_idx=0, direction=1)
    def _E(self): self._rotate_slice(perspective=1, slice_idx=1, direction=-1)
    def _e(self): self._rotate_slice(perspective=1, slice_idx=1, direction=1)
    def _D(self): self._rotate_slice(perspective=1, slice_idx=2, direction=1)
    def _d(self): self._rotate_slice(perspective=1, slice_idx=2, direction=-1)

    def _L(self): self._rotate_slice(perspective=2, slice_idx=0, direction=-1)
    def _l(self): self._rotate_slice(perspective=2, slice_idx=0, direction=1)
    def _S(self): self._rotate_slice(perspective=2, slice_idx=1, direction=-1)
    def _s(self): self._rotate_slice(perspective=2, slice_idx=1, direction=1)
    def _R(self): self._rotate_slice(perspective=2, slice_idx=2, direction=1)
    def _r(self): self._rotate_slice(perspective=2, slice_idx=2, direction=-1)

    def _get_position_of_piece(self, piece_id):
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_positions[i, j, k] == piece_id:
                        return (i, j, k)
        return None # Piece ID not found (should not happen in a valid cube state)

    def _get_piece_at_position(self, position):
        """Returns the piece ID at a given position (i, j, k)."""
        i, j, k = position
        return self.piece_current_positions[i, j, k]
    
    def _get_orientation_of_piece(self, piece_id):
        """Returns the orientation of a piece given its ID."""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_positions[i, j, k] == piece_id:
                        return self.piece_current_orientations[i, j, k]
        return None

    def apply_moves(self, move_sequence):
        if not isinstance(move_sequence, (list, str)):
            raise ValueError("argument to apply_moves must be a list or a string of valid moves")

        if isinstance(move_sequence, str):
            move_sequence = list(move_sequence) # Convert string to list for consistent iteration

        for index, move in enumerate(move_sequence): # More idiomatic and readable way to get index in loop
            if move in self.move_map:
                self._update_corner_orientations(move)
                self._update_edge_orientations(move)
                self.move_map[move]()
            else:
                raise ValueError(f"Invalid move: '{move}' at index {index}") # More readable error message