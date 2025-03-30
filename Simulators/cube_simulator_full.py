import numpy as np
import json
import copy
import os
import ast

class CubeBase:
    tables = None
    @classmethod
    def initialize(cls):
        if cls.tables is None:
            cls.piece_initial_ids_at_positions = np.array([
                [[0 , 1 , 2 ],
                 [3 , 4 , 5 ],
                 [6 , 7 , 8 ],], # Front face

                [[9 , 10, 11],
                 [12, 13, 14],
                 [15, 16, 17],], # Middle slice

                [[18, 19, 20],
                 [21, 22, 23],
                 [24, 25, 26],], # Back face
            ])
            cls.piece_initial_orientations = np.array([
                [['xyZ', 'g', 'XyZ'],
                 ['g'  , 'y', 'g'  ],
                 ['xyz', 'g', 'Xyz']],

                [['g'  , 'Z', 'g'  ],
                 ['x'  , 'C', 'X'  ],
                 ['g'  , 'z', 'g'  ]],

                [['xYZ', 'g', 'XYZ'],
                 ['g'  , 'Y', 'g'  ],
                 ['xYz', 'g', 'XYz']],
            ]) 
            # for corners, capital letters refer to positive axes and lower letters refer to negative axes.
            # so, for the first corner piece (0,0,0), whose orientation is xyZ, the piece's local coordiantes' x-axis's facelet is aligned with the cube's negative x-axis (given by x at the start), y-axis's facelet with the cube's negative y-axis (y), and z-axis's facelet with the cube's positive z-axis (Z).
            # for edges, 'g' (good) means that the minimum-length path from the current position to the initial position (solved state) also solves the edge in isolation, when taken
            # and 'b' (bad) means that the minimum-length path from the current position to the initial position (solved state) does not solve the edge in isolation, when taken. The solution in isolation is what is called the secondary path: path that is immediately of the next length to the minimum-length path to the solved state (called the primary path).
            # the fourteenth piece (the cube center), marked by 'C', is irrelevant to the program.
            # the centers of the faces are marked by the respective axes that align with their respective normals.
            cls.edge_positions, cls.corner_positions = cls.categorize_positions_over_piece_types()
            cls.edge_ids, cls.corner_ids = cls.categorize_ids_over_piece_types()
            cls.tables = cls._load_tables_from_json([
                    '../Precomputed_Tables/corner_position_distance_table.json',
                    '../Precomputed_Tables/edge_position_distance_table.json',
                    '../Precomputed_Tables/position_movement_table.json'
            ])
            cls.edge_distances = cls.tables["edge_distances"]
            cls.corner_distances = cls.tables["corner_distances"]
            cls.movements = cls.tables["movements"]

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
        base_dir = os.path.dirname(__file__)
        tables = {
            "edge_distances": None,
            "corner_distances": None,
            "movements": None
        }
        for filename in filenames:
            file_path = os.path.join(base_dir, filename)  # or incorporate '..', 'Precomputed_Tables'
            try:
                with open(file_path, 'r') as f:
                    serializable_table = json.load(f)
                    
                    # Determine which table type this file contains
                    if 'edge' in filename.lower() and 'distance' in filename.lower():
                        tables["edge_distances"] = {}
                        for pair_str, distance in serializable_table.items():
                            pos_tuple = tuple(ast.literal_eval(pair_str))  # Safely parse using ast.literal_eval
                            tables["edge_distances"][pos_tuple] = distance
                            
                    elif 'corner' in filename.lower() and 'distance' in filename.lower():
                        tables["corner_distances"] = {}
                        for pair_str, distance in serializable_table.items():
                            pos_tuple = tuple(ast.literal_eval(pair_str))  # Consistent parsing
                            tables["corner_distances"][pos_tuple] = distance
                            
                    elif 'position' in filename.lower() and 'movement' in filename.lower():
                        tables["movements"] = {}
                        for move, position_movements in serializable_table.items():
                            movements = {}
                            for from_pos_str, to_pos_str in position_movements.items():
                                from_pos = tuple(ast.literal_eval(from_pos_str))
                                to_pos = tuple(ast.literal_eval(to_pos_str))
                                movements[from_pos] = to_pos
                            tables["movements"][move] = movements
                            
            except Exception as e:
                print(f"Error loading '{filename}': {e}")
        
        # Log which tables were successfully loaded
        loaded_tables = [key for key, value in tables.items() if value is not None]
        if loaded_tables:
            print(f"Successfully loaded tables: {', '.join(loaded_tables)}")
        else:
            print("Warning: No tables were successfully loaded")
            
        return tables

    @classmethod
    def categorize_ids_over_piece_types(cls):
        """Identifies edge and corner pieces based on orientation markers."""
        edge_ids = []
        corner_ids = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = cls.piece_initial_ids_at_positions[i, j, k]
                    if piece_id in [4, 10, 12, 13, 14, 16, 22]:
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
                    piece_id = cls.piece_initial_ids_at_positions[i, j, k]
                    if piece_id in [4, 10, 12, 13, 14, 16, 22]:
                        continue
                    orientation = cls.piece_initial_orientations[i, j, k]
                    if orientation == 'g':
                        edge_positions.append((i, j, k))
                    else:
                        corner_positions.append((i, j, k))
        return edge_positions, corner_positions

class CubeTracker(CubeBase):
    def __init__(self):
        CubeBase.initialize()
        self.piece_current_ids_at_positions = copy.deepcopy(CubeBase.piece_initial_ids_at_positions)
        self.piece_current_orientations = copy.deepcopy(CubeBase.piece_initial_orientations)
        self.move_history = []
        self.affected_piece_ids_per_move = []
        self.affected_piece_positions_per_move = []
        self.cube_current_faces_with_orientations = {
            'y': self.piece_initial_orientations[0, :, :],
            'Y': np.flip(self.piece_initial_orientations[2, :, :], axis=1),
            'X': np.transpose(self.piece_initial_orientations[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_initial_orientations[:, :, 0]), axis=1),
            'Z': np.flip(self.piece_initial_orientations[:, 0, :], axis=0),
            'z': self.piece_initial_orientations[:, 2, :]
        }
        self.cube_current_faces_with_ids = {
            'y': self.piece_initial_ids_at_positions[0, :, :],
            'Y': np.flip(self.piece_initial_ids_at_positions[2, :, :], axis=1),
            'X': np.transpose(self.piece_initial_ids_at_positions[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_initial_ids_at_positions[:, :, 0]), axis=1),
            'Z': np.flip(self.piece_initial_ids_at_positions[:, 0, :], axis=0),
            'z': self.piece_initial_ids_at_positions[:, 2, :]
        }
    
        self.move_map = {
                'L': self._L, 'l': self._l, 'R': self._R, 'r': self._r,
                'F': self._F, 'f': self._f, 'B': self._B, 'b': self._b,
                'U': self._U, 'u': self._u, 'D': self._D, 'd': self._d,
                'N': self._N
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

    def _rotate_face(self, perspective, face_idx, direction):
        """ Rotate a face (0=front, 1=middle, 2=back) seen from the given perspective (0=front, 1=top, 2=left) in the given direction """
        
        def change_perspective(cube, perspective, direction):
            if perspective == 0:
                return cube
            else:
                return np.rot90(cube, k=direction, axes=(0, perspective))
            
        # Convert to the desired perspective, rotate the face, then convert back
        self.piece_current_ids_at_positions = change_perspective(self.piece_current_ids_at_positions, perspective, -1)
        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, -1)

        self.piece_current_ids_at_positions[face_idx] = np.rot90(self.piece_current_ids_at_positions[face_idx], k=direction, axes=(0, 1))
        self.piece_current_orientations[face_idx] = np.rot90(self.piece_current_orientations[face_idx], k=direction, axes=(0, 1))
        
        self.piece_current_ids_at_positions = change_perspective(self.piece_current_ids_at_positions, perspective, 1)
        self.piece_current_orientations = change_perspective(self.piece_current_orientations, perspective, 1)
        
        self.cube_current_faces_with_ids = {
            'y': self.piece_current_ids_at_positions[0, :, :],
            'Y': np.flip(self.piece_current_ids_at_positions[2, :, :], axis=1),
            'X': np.transpose(self.piece_current_ids_at_positions[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_current_ids_at_positions[:, :, 0]), axis=1),
            'Z': np.flip(self.piece_current_ids_at_positions[:, 0, :], axis=0),
            'z': self.piece_current_ids_at_positions[:, 2, :]
        }

        self.cube_current_faces_with_orientations = {
            'y': self.piece_current_orientations[0, :, :],
            'Y': np.flip(self.piece_current_orientations[2, :, :], axis=1),
            'X': np.transpose(self.piece_current_orientations[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_current_orientations[:, :, 0]), axis=1),
            'Z': np.flip(self.piece_current_orientations[:, 0, :], axis=0),
            'z': self.piece_current_orientations[:, 2, :]
        }

    def _F(self): self._rotate_face(0, 0, -1)
    def _f(self): self._rotate_face(0, 0,  1)
    def _B(self): self._rotate_face(0, 2,  1)
    def _b(self): self._rotate_face(0, 2, -1)
    def _U(self): self._rotate_face(1, 0, -1)
    def _u(self): self._rotate_face(1, 0,  1)
    def _D(self): self._rotate_face(1, 2,  1)
    def _d(self): self._rotate_face(1, 2, -1)
    def _L(self): self._rotate_face(2, 0, -1)
    def _l(self): self._rotate_face(2, 0,  1)
    def _R(self): self._rotate_face(2, 2,  1)
    def _r(self): self._rotate_face(2, 2, -1)
    def _N(self): pass

    def _get_affected_positions(self, move):
        """Determine which positions are affected by a given move"""
        affected_positions = list(self.movements[move].keys())
        return affected_positions
        
    def _get_position_of_piece(self, piece_id):
        """Returns the 3D position vector (tuple) of a piece given the piece_id"""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_ids_at_positions[i, j, k] == piece_id:
                        return (i, j, k)

    def _get_piece_at_position(self, position):
        """Returns the piece ID at a given position (i, j, k)."""
        i, j, k = position
        return self.piece_current_ids_at_positions[i, j, k]
    
    def _get_orientation_of_piece(self, piece_id):
        """Returns the orientation of a piece given its ID."""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_ids_at_positions[i, j, k] == piece_id:
                        return self.piece_current_orientations[i, j, k]
    
    def _update_edge_orientations(self, move):
        """Updates the orientations of edges based on the move made """
        if move in self.movements.keys():
            for edge in self.edge_positions:
                if edge in self.movements[move].keys():
                    piece_id = self.piece_current_ids_at_positions[edge]
                    piece_initial_position = tuple(np.argwhere(self.piece_initial_ids_at_positions == piece_id)[0])
                    if self.edge_distances[(piece_initial_position, edge)] == self.edge_distances[(piece_initial_position, self.movements[move][edge])]:
                        current_orientation = self.piece_current_orientations[edge]
                        self.piece_current_orientations[edge] = 'g' if current_orientation=='b' else 'b'
    
    def _update_corner_orientations(self, move):
        """Updates the orientations of corners based on the move made """

        corner_move_vs_facelet_swap_map = {
            'L': ((1,2),'x'), 'l': ((1,2),'x'), 'R': ((1,2),'x'), 'r': ((1,2),'x'),
            'F': ((0,2),'y'), 'f': ((0,2),'y'), 'B': ((0,2),'y'), 'b': ((0,2),'y'),
            'U': ((0,1),'z'), 'u': ((0,1),'z'), 'D': ((0,1),'z'), 'd': ((0,1),'z'),
            'N': ((0,0),'x')
        }

        def remove(lst, item):
            return [x for x in lst if x != item]
        if move in self.movements.keys():
            for corner in self.corner_positions:
                if corner in self.movements[move].keys():
                    current_orientation = list(self.piece_current_orientations[corner])
                    corner_initial_orientation_at_destination = list(self.piece_initial_orientations[self.movements[move][corner]])
                    reference_constant_facelet_id = corner_move_vs_facelet_swap_map[move][1]
                    corner_constant_facelet = ''.join(current_orientation).lower().index(reference_constant_facelet_id)
                    corner_facelets_to_swap = remove(list(range(0, 3)), corner_constant_facelet)
                    corner_facelet_ids_to_swap = [current_orientation[i] for i in corner_facelets_to_swap]
                    corner_constant_facelet_id = current_orientation[corner_constant_facelet]
                    corner_facelet_ids_to_swap_at_destination = remove(corner_initial_orientation_at_destination, corner_constant_facelet_id)
                    zipped = list(zip(corner_facelets_to_swap, corner_facelet_ids_to_swap))
                    for i in zipped:
                        for j in corner_facelet_ids_to_swap_at_destination:
                            if i[1].lower() != j.lower():
                                current_orientation[i[0]] = j
                    self.piece_current_orientations[corner] = ''.join(current_orientation)

    def apply_moves(self, move_sequence):
        """Applies the moves to the cube state (piece_current_positions and piece_current_orientations)
        Args:
            move_sequence(list/str): ordered set of moves as a list or a string
        """
        if not isinstance(move_sequence, (list, str)):
            raise ValueError("argument to apply_moves must be a list or a string of valid moves")
        if isinstance(move_sequence, str):
            move_sequence = list(move_sequence)
        for index, move in enumerate(move_sequence):
            if move in self.move_map:
                self.move_history.append(move)
                affected_piece_positions_item = self._get_affected_positions(move)
                self.affected_piece_positions_per_move.append(affected_piece_positions_item)
                self.affected_piece_ids_per_move.append([int(id) for id in [self.piece_current_ids_at_positions[position] for position in affected_piece_positions_item]])
                self._update_corner_orientations(move)
                self._update_edge_orientations(move)
                self.move_map[move]()
            else:
                raise ValueError(f"Invalid move: '{move}' at index {index}") # More readable error message

class CubeColorizer:
    def __init__(self):
        self.cube_tracker = CubeTracker()
        self.total_move_count = 0
        self.direction__initial_color_map = {
            'X'     : "Red"  , 'x'     : "Orange",
            'Y'     : "Blue" , 'y'     : "Green",
            'Z'     : "White", 'z'     : "Yellow",
            "Red"   : 'X'    , "Orange": 'x',
            "Blue"  : 'Y'    , "Green" : 'y',
            "White" : 'Z'    , "Yellow": 'z',
        }
        self.direction__color_idx_map = {
            'X':  0 , 'x':  1 , 
            'Y':  2 , 'y':  3 , 
            'Z':  4 , 'z':  5 ,
            0  : 'X', 1  : 'x', 
            2  : 'Y', 3  : 'y', 
            4  : 'Z', 5  : 'z',
        }
        self.current_colors = {}
        self.initial_colors = {}
        self.null_color = ["Black" for _ in range(6)]
    
    def update_colors(self):
        """Update the visualization based on current cube state"""
        if self.total_move_count == 0:
            for piece_id in range(0, 27):
                color = copy.deepcopy(self.null_color)
                piece_initial_orientation = list(self.cube_tracker.piece_initial_orientations[tuple([int(x) for x in np.argwhere(self.cube_tracker.piece_initial_ids_at_positions==piece_id).flatten()])])
                for color_idx in range(6):
                    if self.direction__color_idx_map[color_idx] in piece_initial_orientation:
                        color[color_idx] = self.direction__initial_color_map[self.direction__color_idx_map[color_idx]]
                self.initial_colors[piece_id] = color
            self.current_colors = copy.deepcopy(self.initial_colors)

        for idx, move in enumerate(list(self.cube_tracker.move_history)[self.total_move_count:]):
            if move != 'N':
                affected_piece_positions = self.cube_tracker.affected_piece_positions_per_move[self.total_move_count+idx]
                affected_piece_ids = self.cube_tracker.affected_piece_ids_per_move[self.total_move_count+idx]
                for piece_id, position in list(zip(affected_piece_ids, affected_piece_positions)): 
                    self.update_piece_colors(piece_id, position, move)
        self.total_move_count = len(self.cube_tracker.move_history)
        return self.current_colors
        
    def update_piece_colors(self, piece_id, position, move):
        """Update the colors of a piece based on its orientation and position"""
        corner_ids = [int(x) for x in self.cube_tracker.corner_ids]
        if piece_id in corner_ids:
            position_after_move = self.cube_tracker.movements[move][position]
            corner_current_orientation = list(self.cube_tracker.piece_current_orientations[position_after_move])
            corner_initial_orientation = list(self.cube_tracker.piece_initial_orientations[tuple([int(x) for x in np.argwhere(self.cube_tracker.piece_initial_ids_at_positions==piece_id).flatten()])])
            final_color = copy.deepcopy(self.null_color)
            for i in range(3):
                initial_color = self.direction__initial_color_map[corner_initial_orientation[i]]
                current_facelet_id = corner_current_orientation[i]
                final_color[self.direction__color_idx_map[current_facelet_id]] = initial_color
            self.current_colors[piece_id] = final_color

if __name__ == "__main__":
    visualizer = CubeColorizer()
    while True:
        next_moves = input("Enter a move (or 'xx' to quit): ")
        if next_moves == 'xx':
            break
        next_prompt_flag = False
        for idx, move in enumerate(next_moves):
            if move not in visualizer.cube_tracker.move_map:
                print(f"Invalid move: {move} at {idx}. Please try again.")
                next_prompt_flag = True
                break
        if next_prompt_flag:
            continue
        visualizer.cube_tracker.apply_moves(next_moves)
        print(visualizer.update_colors())
        print(visualizer.cube_tracker.move_history)
    print("Exiting...")