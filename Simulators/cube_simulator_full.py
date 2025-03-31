import numpy as np
import json
import copy
import os
import ast
import matplotlib.pyplot as plt
import matplotlib.patches as patches

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
            # for edges, 'g', which stands for 'good', means that the minimum-length path from the current position to the initial position (solved state), which ignores orientation, also solves the edge in isolation when taken. This minimum-length, orientation-ignoring path is called primary path.
            # and 'b' (bad) means that the primary path from the current position to the initial position (solved state) does not solve the edge in isolation, when taken. The solution in isolation is what is called the secondary path: path that is immediately of the next length to the primary path to the solved state of the piece.
            # the fourteenth piece (the cube's absolute center), marked with 'C', is irrelevant to the program.
            # the centers of the faces are marked by the respective axes that align with centers' outward normals.

            cls.edge_positions, cls.corner_positions = cls.categorize_positions_over_piece_types()
            cls.edge_ids, cls.corner_ids = cls.categorize_ids_over_piece_types()
            cls.tables = cls._load_tables_from_json([
                    r'..\Precomputed_Tables\corner_position_distance_table.json',
                    r'..\Precomputed_Tables\edge_position_distance_table.json',
                    r'..\Precomputed_Tables\position_movement_table.json'
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
        tables = {
            "edge_distances": None,
            "corner_distances": None,
            "movements": None
        }
        for filename in filenames:
            file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), filename))
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
        self.affected_piece_ids_for_move = []
        self.affected_piece_positions_for_move = []
        self.cube_current_faces_with_orientations = {
            'X': np.transpose(self.piece_initial_orientations[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_initial_orientations[:, :, 0]), axis=1),
            'y': self.piece_initial_orientations[0, :, :],
            'Y': np.flip(self.piece_initial_orientations[2, :, :], axis=1),
            'Z': np.flip(self.piece_initial_orientations[:, 0, :], axis=0),
            'z': self.piece_initial_orientations[:, 2, :]
        }
        self.cube_current_faces_with_ids = {
            'X': np.transpose(self.piece_initial_ids_at_positions[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_initial_ids_at_positions[:, :, 0]), axis=1),
            'y': self.piece_initial_ids_at_positions[0, :, :],
            'Y': np.flip(self.piece_initial_ids_at_positions[2, :, :], axis=1),
            'Z': np.flip(self.piece_initial_ids_at_positions[:, 0, :], axis=0),
            'z': self.piece_initial_ids_at_positions[:, 2, :]
        }
    
        self.move_map = {
                'L': self.__L, 'l': self.__l, 'R': self.__R, 'r': self.__r,
                'F': self.__F, 'f': self.__f, 'B': self.__B, 'b': self.__b,
                'U': self.__U, 'u': self.__u, 'D': self.__D, 'd': self.__d,
                'N': self.__N
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

    def __rotate_face(self, perspective, face_idx, direction):
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
            'X': np.transpose(self.piece_current_ids_at_positions[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_current_ids_at_positions[:, :, 0]), axis=1),
            'y': self.piece_current_ids_at_positions[0, :, :],
            'Y': np.flip(self.piece_current_ids_at_positions[2, :, :], axis=1),
            'Z': np.flip(self.piece_current_ids_at_positions[:, 0, :], axis=0),
            'z': self.piece_current_ids_at_positions[:, 2, :]
        }

        self.cube_current_faces_with_orientations = {
            'X': np.transpose(self.piece_current_orientations[:, :, 2]),
            'x': np.flip(np.transpose(self.piece_current_orientations[:, :, 0]), axis=1),
            'y': self.piece_current_orientations[0, :, :],
            'Y': np.flip(self.piece_current_orientations[2, :, :], axis=1),
            'Z': np.flip(self.piece_current_orientations[:, 0, :], axis=0),
            'z': self.piece_current_orientations[:, 2, :]
        }

    def __F(self): self.__rotate_face(0, 0, -1)
    def __f(self): self.__rotate_face(0, 0,  1)
    def __B(self): self.__rotate_face(0, 2,  1)
    def __b(self): self.__rotate_face(0, 2, -1)
    def __U(self): self.__rotate_face(1, 0, -1)
    def __u(self): self.__rotate_face(1, 0,  1)
    def __D(self): self.__rotate_face(1, 2,  1)
    def __d(self): self.__rotate_face(1, 2, -1)
    def __L(self): self.__rotate_face(2, 0, -1)
    def __l(self): self.__rotate_face(2, 0,  1)
    def __R(self): self.__rotate_face(2, 2,  1)
    def __r(self): self.__rotate_face(2, 2, -1)
    def __N(self): pass

    def get_affected_positions(self, move):
        """Determine which positions are affected by a given move"""
        affected_positions = [key for key in self.movements[move].keys() if key != self.movements[move][key]]
        return affected_positions
        
    def get_position_of_piece(self, piece_id):
        """Returns the 3D position vector (tuple) of a piece given the piece_id"""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_ids_at_positions[i, j, k] == piece_id:
                        return (i, j, k)

    def get_piece_at_position(self, position):
        """Returns the piece ID at a given position (i, j, k)."""
        i, j, k = position
        return self.piece_current_ids_at_positions[i, j, k]
    
    def get_orientation_of_piece(self, piece_id):
        """Returns the orientation of a piece given its ID."""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_ids_at_positions[i, j, k] == piece_id:
                        return self.piece_current_orientations[i, j, k]
    
    def __update_edge_orientations(self, move):
        """Updates the orientations of edges based on the move made """
        if move in self.move_map.keys():
            for edge in self.edge_positions:
                if edge != self.movements[move][edge]:
                    piece_id = self.piece_current_ids_at_positions[edge]
                    piece_initial_position = tuple(np.argwhere(self.piece_initial_ids_at_positions == piece_id)[0])
                    if self.edge_distances[(piece_initial_position, edge)] == self.edge_distances[(piece_initial_position, self.movements[move][edge])]:
                        current_orientation = self.piece_current_orientations[edge]
                        self.piece_current_orientations[edge] = 'g' if current_orientation=='b' else 'b'
    
    def __update_corner_orientations(self, move):
        """Updates the orientations of corners based on the move made """

        corner_move_vs_facelet_swap_map = {
            'L': ((1,2),'x'), 'l': ((1,2),'x'), 'R': ((1,2),'x'), 'r': ((1,2),'x'),
            'F': ((0,2),'y'), 'f': ((0,2),'y'), 'B': ((0,2),'y'), 'b': ((0,2),'y'),
            'U': ((0,1),'z'), 'u': ((0,1),'z'), 'D': ((0,1),'z'), 'd': ((0,1),'z'),
            'N': ((0,0),'x')
        }

        def remove(lst, item):
            return [x for x in lst if x != item]
        
        if move in self.move_map.keys():
            for corner in self.corner_positions:
                if corner != self.movements[move][corner]:
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
                affected_piece_positions_item = self.get_affected_positions(move)
                self.affected_piece_positions_for_move.append(affected_piece_positions_item)
                self.affected_piece_ids_for_move.append([int(id) for id in [self.piece_current_ids_at_positions[position] for position in affected_piece_positions_item]])
                self.__update_corner_orientations(move)
                self.__update_edge_orientations(move)
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
                affected_piece_positions = self.cube_tracker.affected_piece_positions_for_move[self.total_move_count+idx]
                affected_piece_ids = self.cube_tracker.affected_piece_ids_for_move[self.total_move_count+idx]
                for piece_id, position in list(zip(affected_piece_ids, affected_piece_positions)): 
                    self.__update_piece_colors(piece_id, position, move)
        self.total_move_count = len(self.cube_tracker.move_history)
        return self.current_colors
        
    def __update_piece_colors(self, piece_id, position, move):
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

class CubeVisualizer2D:
    def __init__(self):
        self.colorizer = CubeColorizer()
        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        self.fig.canvas.manager.set_window_title('Rubik\'s Cube 2D')
        self.colors_rgb = {
            "White":  '#FFFFFF', "Yellow": '#FBFB45',
            "Blue" :  '#4095FE', "Green" : '#00EF2A',
            "Red"  :  '#FF0000', "Orange": '#FF8800',
            "Black":  '#333333',
        }
        self.grid_positions = {
            'Z': (3, 6),  # White face (Up)
            'x': (0, 3),  # Orange face (Left)
            'y': (3, 3),  # Green face (Front)
            'X': (6, 3),  # Red face (Right)
            'Y': (9, 3),  # Blue face (Back) - Unfolded to the far right
            'z': (3, 0),  # Yellow face (Down)
        }
        self.colorizer.cube_tracker.apply_moves('N')
        self.update_display()
    
    def apply_moves(self, moves):
        self.colorizer.cube_tracker.apply_moves(moves)

    def update_display(self):
        self.ax.clear()
        min_x = min(pos[0] for pos in self.grid_positions.values())
        max_x = max(pos[0] + 3 for pos in self.grid_positions.values()) # Add 3 for width
        min_y = min(pos[1] for pos in self.grid_positions.values())
        max_y = max(pos[1] + 3 for pos in self.grid_positions.values()) # Add 3 for height

        # Apply limits with some padding
        self.ax.set_xlim(min_x - 0.5, max_x + 0.5)
        self.ax.set_ylim(min_y - 0.5, max_y + 0.5)

        # Ensure squares are square
        self.ax.set_aspect('equal', adjustable='box')

        face_to_colors_map = {}
        new_colors = self.colorizer.update_colors()
        for direction in ['X', 'x', 'Y', 'y', 'Z', 'z']:
            face_colors = np.full((3, 3), '#000000')
            for piece_id in self.colorizer.cube_tracker.cube_current_faces_with_ids[direction].flatten():
                face_colors[tuple(np.argwhere(self.colorizer.cube_tracker.cube_current_faces_with_ids[direction]==piece_id)[0])] = new_colors[piece_id][self.colorizer.direction__color_idx_map[direction]]
            face_to_colors_map[direction] = face_colors
        
        for direction in ['X', 'x', 'Y', 'y', 'Z', 'z']:
            for i in range(3):
                for j in range(3):
                    color_patch = patches.Rectangle(
                        (self.grid_positions[direction][0]+j, self.grid_positions[direction][1]+2-i),
                        1,1,
                        facecolor=self.colors_rgb[face_to_colors_map[direction][i,j]],
                        edgecolor='black',
                        linewidth=1,
                    )
                    self.ax.add_patch(color_patch)

if __name__ == "__main__":
    visualizer = CubeVisualizer2D()
    print("Enter a scrambling move sequence.\nValid moves: N, F, f, B, b, R, r, U, u, D, d, L, l\n(Enter 'x' to quit)\n:", end='')
    while True:
        next_moves = input()
        if not plt.isinteractive():
            plt.ion()
        plt.pause(0.1)
        if next_moves.lower() != 'x':
            valid_moves = True
            for idx, move in enumerate(next_moves):
                if move not in visualizer.colorizer.cube_tracker.move_map.keys():
                    print(f"Error: Invalid move '{move}' at index {idx}. Try again:")
                    valid_moves = False
                    break
            if not valid_moves:
                continue
            else:
                visualizer.apply_moves(next_moves)
                visualizer.update_display()
                print("\nPlot window is active. Close the plot window to exit the script.")
                plt.ioff()
                plt.show()
                print("Move history:",''.join(visualizer.colorizer.cube_tracker.move_history))
                break
        else:
            plt.ioff()
            plt.close(visualizer.fig)
            print("Move history:",''.join(visualizer.colorizer.cube_tracker.move_history))
            break