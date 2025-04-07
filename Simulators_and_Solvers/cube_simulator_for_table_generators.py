import numpy as np
import copy

class Cube:
    def __init__(self):
        # The PIECES are counted from Left-to-Right(axis=2), Top-to-Bottom (axis=1), and Front-to-Back (axis=0), in that order. The fourteenth piece is the invisible and irrelevant center-most piece of the cube
        self.piece_initial_ids_at_positions = np.array([
            [[0 , 1 , 2 ],
             [3 , 4 , 5 ],
             [6 , 7 , 8 ]], # Front face

            [[9 , 10, 11],
             [12, 13, 14],
             [15, 16, 17]], # Middle slice

            [[18, 19, 20],
             [21, 22, 23],
             [24, 25, 26]], # Back face
        ])

        self.piece_initial_orientations = np.array([
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

        # Define positions for edges and corners
        self.piece_current_ids_at_positions = copy.deepcopy(self.piece_initial_ids_at_positions)
        self.piece_current_orientations = copy.deepcopy(self.piece_initial_orientations)

        # Call the piece-categorizing methods and store them           
        self.edge_positions, self.corner_positions = self.categorize_positions_over_piece_types()
        self.edge_ids, self.corner_ids = self.categorize_ids_over_piece_types()

        # Sort positions and ids for consistent ordering
        self.edge_positions.sort()
        self.corner_positions.sort()
        self.edge_ids.sort()
        self.corner_ids.sort()

        # changed to HTM (added new moves L2, F2, ...)
        self.move_map = {
                'L': self.__L, 'L2': self.__L2, 'L\'': self.__l, 'R': self.__R, 'R2': self.__R2, 'R\'': self.__r,
                'F': self.__F, 'F2': self.__F2, 'F\'': self.__f, 'B': self.__B, 'B2': self.__B2, 'B\'': self.__b,
                'U': self.__U, 'U2': self.__U2, 'U\'': self.__u, 'D': self.__D, 'D2': self.__D2, 'D\'': self.__d,
                'N': self.__N
        }
        # The uppercase letters are the clockwise moves, and the lowercase letters are the counter-clockwise moves

    def categorize_ids_over_piece_types(self):
        """Identifies edge and corner pieces based on orientation markers."""
        edge_ids = []
        corner_ids = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = self.piece_initial_ids_at_positions[i, j, k]
                    if piece_id in [4, 10, 12, 13, 14, 16, 22]:
                        continue
                    orientation = self.piece_initial_orientations[i, j, k]
                    if orientation == 'g':  # edge
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
                    if self.piece_current_ids_at_positions[i, j, k] in [4, 10, 12, 13, 14, 16, 22]:
                        continue
                    else:
                        if self.piece_current_orientations[i, j, k] == 'g':
                            edge_positions.append((i, j, k))
                        else:
                            corner_positions.append((i, j, k))
        return edge_positions, corner_positions
    
    def __rotate_face(self, perspective, slice_idx, direction):
        """ Rotate a face (0=front, 1=middle, 2=back) seen from the given perspective (0=front, 1=top, 2=left) in the given direction """
        def change_perspective(cube, perspective, direction):
            if perspective == 0: return cube
            else: return np.rot90(cube, k=direction, axes=(0, perspective))
        # Convert to the desired perspective, rotate the slice, then convert back
        self.piece_current_ids_at_positions = change_perspective(self.piece_current_ids_at_positions, perspective, -1)
        self.piece_current_ids_at_positions[slice_idx] = np.rot90(self.piece_current_ids_at_positions[slice_idx], k=direction, axes=(0, 1))
        self.piece_current_ids_at_positions = change_perspective(self.piece_current_ids_at_positions, perspective, 1)

    def __F(self) : self.__rotate_face(0, 0, -1)
    def __F2(self): self.__rotate_face(0, 0, -2)
    def __f(self) : self.__rotate_face(0, 0,  1)
    def __B(self) : self.__rotate_face(0, 2,  1)
    def __B2(self): self.__rotate_face(0, 2,  2)
    def __b(self) : self.__rotate_face(0, 2, -1)
    def __U(self) : self.__rotate_face(1, 0, -1)
    def __U2(self): self.__rotate_face(1, 0, -2)
    def __u(self) : self.__rotate_face(1, 0,  1)
    def __D(self) : self.__rotate_face(1, 2,  1)
    def __D2(self): self.__rotate_face(1, 2,  2)
    def __d(self) : self.__rotate_face(1, 2, -1)
    def __L(self) : self.__rotate_face(2, 0, -1)
    def __L2(self): self.__rotate_face(2, 0, -2)
    def __l(self) : self.__rotate_face(2, 0,  1)
    def __R(self) : self.__rotate_face(2, 2,  1)
    def __R2(self): self.__rotate_face(2, 2,  2)
    def __r(self) : self.__rotate_face(2, 2, -1)
    def __N(self) : pass

    def get_position_of_piece(self, piece_id):
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if self.piece_current_ids_at_positions[i, j, k] == piece_id:
                        return (i, j, k)
        return None

    def get_piece_at_position(self, position):
        """Returns the piece ID at a given position (i, j, k)."""
        i, j, k = position
        return self.piece_current_ids_at_positions[i, j, k]

    def apply_moves(self, move_sequence):
        """Applies the moves to the cube state (piece_current_positions and piece_current_orientations)
        Args:
            move_sequence(list/str): ordered set of moves as a list or a string
        """
        if not isinstance(move_sequence, str):
            raise ValueError("argument to apply_moves must be a continuous string of valid moves")
        
        idx = 0
        moves_split = []
        while True:
            if idx <= len(move_sequence)-2 and move_sequence[idx:idx+2] in self.move_map.keys():
                moves_split.append(move_sequence[idx:idx+2])
                idx += 2
                if idx >= len(move_sequence):
                    break
            elif move_sequence[idx] in self.move_map.keys():
                moves_split.append(move_sequence[idx])
                idx += 1
                if idx >= len(move_sequence):
                    break
            else:
                raise ValueError(f"Invalid entry at index {idx}")
            
        for move in moves_split:
            self.move_map[move]()