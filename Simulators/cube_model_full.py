import numpy as np
import networkx as nx
import json
import copy

class CubeBase:
    tables = None
    piece_initial_positions = np.array([
                    [[1 , 2 , 3 ], [4 , 5 , 6 ], [7 , 8 , 9 ]],
                    [[10, 11, 12], [13, 14, 15], [16, 17, 18]],
                    [[19, 20, 21], [22, 23, 24], [25, 26, 27]]
    ])
    piece_initial_orientations = np.array([
                    [['xyz', 'g', 'xyz'], ['g', 'y', 'g'], ['xyz', 'g', 'xyz']],
                    [['g'  , 'Z', 'g'  ], ['x', 'C', 'X'], ['g'  , 'z', 'g'  ]],
                    [['xyz', 'g', 'xyz'], ['g', 'Y', 'g'], ['xyz', 'g', 'xyz']],
    ])
    @classmethod
    def initialize(cls):
        if cls.tables is None:
            cls.edge_positions, cls.corner_positions = cls.categorize_positions_over_piece_types()
            cls.edge_ids, cls.corner_ids = cls.categorize_ids_over_piece_types()

            cls.edge_positions.sort()
            cls.corner_positions.sort()
            cls.edge_ids.sort()
            cls.corner_ids.sort()

            cls.tables = cls._load_tables_from_json([
                    '../Precomputed_Tables/corner_position_distance_table.json',
                    '../Precomputed_Tables/edge_position_distance_table.json',
                    '../Precomputed_Tables/position_movement_table.json'
            ])
            cls.edge_distances = cls.tables["edge_distances"]
            cls.corner_distances = cls.tables["corner_distances"]
            cls.movements = cls.tables["movements"]

    @classmethod
    def categorize_ids_over_piece_types(cls):
        """Identifies edge and corner pieces based on orientation markers."""
        edge_ids = []
        corner_ids = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = cls.piece_initial_positions[i, j, k]
                    if piece_id in [5, 11, 13, 14, 15, 17, 23]:
                        continue  # Skip center pieces and non-cubies
                    orientation = cls.piece_initial_orientations[i, j, k]
                    if orientation == 'g':
                        edge_ids.append(piece_id)
                    elif orientation == 'xyz':
                        corner_ids.append(piece_id)
        return edge_ids, corner_ids
    
    @classmethod
    def categorize_positions_over_piece_types(cls):
        """ Iterate through all positions in the cube and sort their positions into edges and corners """
        edge_positions = []
        corner_positions = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = cls.piece_initial_positions[i, j, k]
                    if piece_id in [5, 11, 13, 14, 15, 17, 23]:
                        continue
                    orientation = cls.piece_initial_orientations[i, j, k]
                    if orientation == 'g':
                        edge_positions.append((i, j, k))
                    elif orientation == 'xyz':
                        corner_positions.append((i, j, k))
        return edge_positions, corner_positions

    @staticmethod
    def _load_tables_from_json(filenames: list):
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
    
class CubeTracker(CubeBase):
    def __init__(self):
        CubeBase.initialize()
        self.piece_current_positions = copy.deepcopy(CubeBase.piece_initial_positions)
        self.piece_current_orientations = copy.deepcopy(CubeBase.piece_initial_orientations)
    
        self.move_map = {
                'U': self._U, 'F': self._F, 'B': self._B, 'D': self._D, 'L': self._L, 'R': self._R,
                'u': self._u, 'f': self._f, 'b': self._b, 'd': self._d, 'l': self._l, 'r': self._r,
                'M': self._M, 'E': self._E, 'S': self._S, 'm': self._m, 'e': self._e, 's': self._s,
                'N': self._N
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

        self.corner_piece_move_vs_orientation_map = {
            'U': lambda orientation: orientation[1] + orientation[0] + orientation[2],
            'u': lambda orientation: orientation[1] + orientation[0] + orientation[2],
            'D': lambda orientation: orientation[1] + orientation[0] + orientation[2],
            'd': lambda orientation: orientation[1] + orientation[0] + orientation[2],
            'L': lambda orientation: orientation[0] + orientation[2] + orientation[1],
            'l': lambda orientation: orientation[0] + orientation[2] + orientation[1],
            'R': lambda orientation: orientation[0] + orientation[2] + orientation[1],
            'r': lambda orientation: orientation[0] + orientation[2] + orientation[1],
            'F': lambda orientation: orientation[2] + orientation[1] + orientation[0],
            'f': lambda orientation: orientation[2] + orientation[1] + orientation[0],
            'B': lambda orientation: orientation[2] + orientation[1] + orientation[0],
            'b': lambda orientation: orientation[2] + orientation[1] + orientation[0],
            'N': lambda orientation: orientation
        }

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

    def _N(self): pass

    def map_moves_to_inverse_moves(self):
        all_moves = self.move_map.keys()
        moves = []
        inverse_moves = []
        for move in all_moves:
            if move.isupper():
                moves.append(move)
            else:
                inverse_moves.append(move)
        moves.remove('N')
        moves.sort()
        inverse_moves.sort()
        return list(zip(moves, inverse_moves))
        

    def _get_position_of_piece(self, piece_id):
        """Returns the 3D position vector (tuple) given the piece_id"""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_positions[i, j, k] == piece_id:
                        return (i, j, k)

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
    
    def _update_edge_orientations(self, move):
        """ Update the orientations of edges based on the move made """
        for edge in self.edge_positions:
            if move in self.movements.keys():
                if edge in self.movements[move].keys():
                    piece_id = self.piece_current_positions[edge]
                    piece_initial_position = tuple(np.argwhere(self.piece_initial_positions == piece_id)[0])
                    if self.edge_distances[(piece_initial_position, edge)] == self.edge_distances[(piece_initial_position, self.movements[move][edge])]:
                        current_orientation = self.piece_current_orientations[edge]
                        self.piece_current_orientations[edge] = 'g' if current_orientation=='b' else 'b'
    
    def _update_corner_orientations(self, move):
        """ Update the orientations of corners based on the move made """
        for corner in self.corner_positions:
            if move in self.movements.keys():
                if corner in self.movements[move].keys():
                    current_orientation = self.piece_current_orientations[corner]
                    self.piece_current_orientations[corner] = self.corner_piece_move_vs_orientation_map[move](current_orientation)

    def apply_moves(self, move_sequence):
        """Applies the moves to the cube state (piece_current_positions and piece_current_orientations)
        Args:
            move_sequence(list/str): a list or string of valid moves to be made, in order
        """
        if not isinstance(move_sequence, (list, str)):
            raise ValueError("argument to apply_moves must be a list or a string of valid moves")

        if isinstance(move_sequence, str):
            move_sequence = list(move_sequence) # Convert string to list for consistent iteration

        for index, move in enumerate(move_sequence):
            if move in self.move_map:
                self._update_corner_orientations(move)
                self._update_edge_orientations(move)
                self.move_map[move]()
            else:
                raise ValueError(f"Invalid move: '{move}' at index {index}") # More readable error message