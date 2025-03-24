import numpy as np
import networkx as nx
import json
import copy
import sys
import os
sys.path.insert(0, os.path.abspath('..'))

class CubeBase:
    tables = None
    piece_initial_positions = np.array([
        [[1 , 2 , 3 ], [4 , 5 , 6 ], [7 , 8 , 9 ]],
        [[10, 11, 12], [13, 14, 15], [16, 17, 18]],
        [[19, 20, 21], [22, 23, 24], [25, 26, 27]],
    ])
    piece_initial_orientations = np.array([
        [['xyZ', 'g', 'XyZ'], ['g', 'y', 'g'], ['xyz', 'g', 'Xyz']],
        [['g'  , 'Z', 'g'  ], ['x', 'C', 'X'], ['g'  , 'z', 'g'  ]],
        [['xYZ', 'g', 'XYZ'], ['g', 'Y', 'g'], ['xYz', 'g', 'XYz']],
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
                    os.path.join(os.path.dirname(__file__), '..', 'Precomputed_Tables', 'corner_position_distance_table.json'),
                    os.path.join(os.path.dirname(__file__), '..', 'Precomputed_Tables', 'edge_position_distance_table.json'),
                    os.path.join(os.path.dirname(__file__), '..', 'Precomputed_Tables', 'position_movement_table.json')
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
                        continue
                    orientation = cls.piece_initial_orientations[i, j, k]
                    if orientation == 'g':
                        edge_ids.append(piece_id)
                    else:
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
                    else:
                        corner_positions.append((i, j, k))
        return edge_positions, corner_positions

    @staticmethod
    def _load_tables_from_json(filenames: list):
        """
        Loads precomputed tables from JSON files and returns them in a dictionary.

        Args:
            filenames: List of JSON filenames containing the precomputed tables

        Returns:
            dict: A dictionary containing loaded tables, with keys: "edge_distances", "corner_distances", "movements".
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
                'N': self._N
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

        self.corner_move_vs_facelet_swap_map = {
            'L': ((1,2),'x'), 'l': ((1,2),'x'), 'R': ((1,2),'x'), 'r': ((1,2),'x'),
            'F': ((0,2),'y'), 'f': ((0,2),'y'), 'B': ((0,2),'y'), 'b': ((0,2),'y'),
            'U': ((0,1),'z'), 'u': ((0,1),'z'), 'D': ((0,1),'z'), 'd': ((0,1),'z'),
            'N': (0,0),
        }

    def _rotate_face(self, perspective, face_idx, direction):
        """ Rotate a face (0=front, 1=middle, 2=back) seen from the given perspective (0=front, 1=top, 2=left) in the given direction """
        def change_perspective(cube, perspective, direction):
            if perspective == 0: return cube
            else: return np.rot90(cube, k=direction, axes=(0, perspective))
        # Convert to the desired perspective, rotate the face, then convert back
        self.piece_current_positions = change_perspective(self.piece_current_positions, perspective, -1)
        self.piece_current_positions[face_idx] = np.rot90(self.piece_current_positions[face_idx], k=direction, axes=(0, 1))
        self.piece_current_positions = change_perspective(self.piece_current_positions, perspective, 1)

        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, -1)
        self.piece_current_orientations[face_idx] = np.rot90(self.piece_current_orientations[face_idx], k=direction, axes=(0, 1))
        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, 1)

    def _F(self): self._rotate_face(0, 0, -1)
    def _f(self): self._rotate_face(0, 0, 1)
    def _B(self): self._rotate_face(0, 2, 1)
    def _b(self): self._rotate_face(0, 2, -1)
    def _U(self): self._rotate_face(1, 0, -1)
    def _u(self): self._rotate_face(1, 0, 1)
    def _D(self): self._rotate_face(1, 2, 1)
    def _d(self): self._rotate_face(1, 2, -1)
    def _L(self): self._rotate_face(2, 0, -1)
    def _l(self): self._rotate_face(2, 0, 1)
    def _R(self): self._rotate_face(2, 2, 1)
    def _r(self): self._rotate_face(2, 2, -1)
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
        """Returns the 3D position vector (tuple) of a piece given the piece_id"""
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
        """Updates the orientations of edges based on the move made """
        for edge in self.edge_positions:
            if move in self.movements.keys():
                if edge in self.movements[move].keys():
                    piece_id = self.piece_current_positions[edge]
                    piece_initial_position = tuple(np.argwhere(self.piece_initial_positions == piece_id)[0])
                    if self.edge_distances[(piece_initial_position, edge)] == self.edge_distances[(piece_initial_position, self.movements[move][edge])]:
                        current_orientation = self.piece_current_orientations[edge]
                        self.piece_current_orientations[edge] = 'g' if current_orientation=='b' else 'b'
    
    def _update_corner_orientations(self, move):
        """Updates the orientations of corners based on the move made """

        def remove(lst, item):
            return [x for x in lst if x != item]
        
        for corner in self.corner_positions:
            if move in self.movements.keys():
                if corner in self.movements[move].keys():
                    current_orientation = list(self.piece_current_orientations[corner])
                    corner_initial_orientation = self.piece_initial_orientations[corner]
                    final_corner_orientation = list(self.piece_initial_orientations[CubeBase.movements[move][corner]])
                    reference_orientation = list(corner_initial_orientation.lower())
                    reference_constant_facelet_id = self.corner_move_vs_facelet_swap_map[move][1]
                    reference_constant_facelet = reference_orientation.index(reference_constant_facelet_id)
                    corner_constant_facelet = ''.join(current_orientation).lower().index(reference_constant_facelet_id)
                    final_corner_constant_facelet_id = final_corner_orientation[reference_constant_facelet]
                    corner_facelets_to_swap = remove(list(range(0, len(reference_orientation))), corner_constant_facelet)
                    corner_facelet_ids_to_swap = remove(current_orientation, current_orientation[corner_constant_facelet])
                    
                    zipped = list(zip(corner_facelet_ids_to_swap, corner_facelets_to_swap))
                    new_orientation = list(range(0,3))
                    count = 1
                    for id, facelet in zipped:
                        if count == 1:
                            next = final_corner_orientation.pop(reference_orientation.index(id.lower()))
                            final_corner_orientation.remove(final_corner_constant_facelet_id)
                            new_orientation[facelet] = final_corner_orientation[0]
                        else:
                            new_orientation[facelet] = next
                        if count == 2:
                            break
                        count += 1
    
                    new_orientation[corner_constant_facelet] = final_corner_constant_facelet_id
                    print(new_orientation)
                    new_orientation = ''.join(new_orientation)
                    self.piece_current_orientations[corner] = new_orientation

    def apply_moves(self, move_sequence):
        """Applies the moves to the cube state (piece_current_positions and piece_current_orientations)
        Args:
            move_sequence(list/str): ordered set of moves as a list or a string
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
            
if __name__ == "__main__":
    # test for the above simulation model
    c = CubeTracker()
    #c.apply_moves("b")  # Apply the scramble moves to the cube
    c.apply_moves("FR")   # Apply the scramble moves to the cube
    print(c.piece_current_positions)
    print(c.piece_current_orientations)