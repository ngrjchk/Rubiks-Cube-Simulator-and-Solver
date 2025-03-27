# visual_simulator.py
import sys
import time
from cube_simulator_full import *
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    NodePath, Point3, Vec3, VBase4, Material,
    AmbientLight, loadPrcFileData
)
from direct.interval.IntervalGlobal import Sequence, LerpHprInterval, Func

# --- Panda3D Config ---
loadPrcFileData('', 'window-title Rubik\'s Cube Simulator')
loadPrcFileData('', 'sync-video #f')
loadPrcFileData('', 'show-frame-rate-meter #t')
loadPrcFileData('', 'clock-mode limited')
loadPrcFileData('', 'clock-frame-rate 30')  # Reduced target FPS
loadPrcFileData('', 'framebuffer-multisample 1')  # Enable MSAA
loadPrcFileData('', 'multisamples 4')  # 4x Anti-Aliasing

class StaticCubeViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.cube_tracker = CubeTracker()
        self.piece_id_to_node = {}

        # --- Colors ---
        self.colors = {
            "White":  VBase4(0.9, 0.9, 0.9, 1), "Yellow": VBase4(0.9, 0.9, 0.0, 1),
            "Blue":   VBase4(0.0, 0.0, 0.8, 1), "Green":  VBase4(0.0, 0.6, 0.0, 1),
            "Red":    VBase4(0.8, 0.0, 0.0, 1), "Orange": VBase4(1.0, 0.5, 0.0, 1),
            "Black":  VBase4(0.1, 0.1, 0.1, 1),
        }

        # --- Mappings ---
        self.normal_to_solved_color = {
             (1, 0, 0): "Orange",    (-1, 0, 0): "Red",
             (0, 1, 0): "Green",     (0, -1, 0): "Blue",
             (0, 0, 1): "White",     (0, 0, -1): "Yellow",
        }
        self.normal_to_material_name_map = {
             (-1, 0, 0): "mat_pos_x", (1, 0, 0): "mat_neg_x",
             (0, -1, 0): "mat_pos_y", (0, 1, 0): "mat_neg_y",
             (0, 0, 1): "mat_pos_z", (0, 0, -1): "mat_neg_z",
        }

        self.cubie_nodes = {}

        # --- Scene Setup ---
        self.disableMouse()
        self.camera.setPos(0, -15, 3)
        self.camera.lookAt(0, 0, 0)
        self.setBackgroundColor(0.2, 0.2, 0.2)

        # --- Lighting ---
        alight = AmbientLight('ambient_light')
        alight.setColor((1.0, 1.0, 1.0, 1.0))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        # --- Load Cubie Model ---
        try:
            self.cubie_model = self.loader.loadModel("models/cube.egg")
            if not self.cubie_model:
                raise IOError("Model not loaded")
        except Exception as e:
            print(f"FATAL: Could not load model: {e}")
            sys.exit()

        # --- Cube Hierarchy ---
        self.cube_node = self.render.attachNewNode("cube_pivot")
        self.rotation_pivot = self.cube_node.attachNewNode("rotation_pivot")  # Fixed: Parent to cube_node

        # --- Build Cube ---
        self._build_static_cube()

        # --- Interaction ---
        self.accept('mouse1', self.start_drag)
        self.accept('mouse1-up', self.stop_drag)
        self.taskMgr.add(self.drag_cube_task, "dragCubeTask")
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.accept('escape', sys.exit)
        self.accept('u', self.trigger_animation, ['U'])
        self.accept('shift-u', self.trigger_animation, ['u'])
        self.accept('r', self.trigger_animation, ['R'])
        self.accept('shift-r', self.trigger_animation, ['r'])
        self.accept('l', self.trigger_animation, ['L'])
        self.accept('shift-l', self.trigger_animation, ['l'])
        self.accept('f', self.trigger_animation, ['F'])
        self.accept('shift-f', self.trigger_animation, ['f'])
        self.accept('b', self.trigger_animation, ['B'])
        self.accept('shift-b', self.trigger_animation, ['b'])
        self.accept('d', self.trigger_animation, ['D'])
        self.accept('shift-d', self.trigger_animation, ['d'])

        # --- Animation State ---
        self.is_animating = False
        self.animation_speed = 0.25

        print("Cube Simulator Initialized (Local Axis Fix Applied)")
    # --- Mouse Drag Handling ---
    def start_drag(self):
        if self.mouseWatcherNode.hasMouse():
            self.dragging = True
            self.last_mouse_x = self.mouseWatcherNode.getMouseX()
            self.last_mouse_y = self.mouseWatcherNode.getMouseY()

    def stop_drag(self):
        self.dragging = False

    def drag_cube_task(self, task):
        if self.dragging and self.mouseWatcherNode.hasMouse():
            mx = self.mouseWatcherNode.getMouseX()
            my = self.mouseWatcherNode.getMouseY()
            dx = mx - self.last_mouse_x
            dy = my - self.last_mouse_y
            self.cube_node.setH(self.cube_node.getH() + dx * 180)
            self.cube_node.setP(self.cube_node.getP() - dy * 180)
            self.last_mouse_x = mx
            self.last_mouse_y = my
        return task.cont


    def _build_static_cube(self):
        """Build cubies and map them to piece IDs."""
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    piece_id = self.cube_tracker.piece_initial_ids_at_positions[i, j, k]
                    cubie_node = self.render.attachNewNode(f"cubie_{piece_id}")
                    self.cubie_model.copyTo(cubie_node)
                    cubie_node.reparentTo(self.cube_node)
                    cubie_node.setPos(self._get_panda_pos(i, j, k))
                    self._color_cubie(cubie_node, (i, j, k))
                    self.piece_id_to_node[piece_id] = cubie_node

    def _get_panda_pos(self, i, j, k):
        """Convert cube indices to Panda3D coordinates."""
        scale = 1.02
        offset = 1.0
        return Point3(
            (k - offset) * scale,
            (offset - i) * scale,
            (offset - j) * scale
        )

    def _color_cubie(self, node, indices):
        """Color cubie faces - outer layers get colors, inner faces are black."""
        for normal_vec, material_name in self.normal_to_material_name_map.items():
            mat = node.findMaterial(material_name)
            if mat:
                # Determine if this face is on the outer layer
                is_outer_face = False
                if (abs(normal_vec[0]) > 0.5 and (indices[2] in [0, 2])) or \
                   (abs(normal_vec[1]) > 0.5 and (indices[0] in [0, 2])) or \
                   (abs(normal_vec[2]) > 0.5 and (indices[1] in [0, 2])):
                    is_outer_face = True

                # Set color
                color = self.colors["Black"]
                if is_outer_face:
                    color_name = {
                        (-1, 0, 0): "Red",    (1, 0, 0): "Orange",
                        (0, -1, 0): "Blue",   (0, 1, 0): "Green",
                        (0, 0, 1): "White",  (0, 0, -1): "Yellow",
                    }[normal_vec]
                    color = self.colors[color_name]
                
                mat.setAmbient(color)
                mat.setDiffuse(color)
    # Add these methods to the StaticCubeViewer class:

    def trigger_animation(self, move):
        """Handle move input and trigger animation."""
        if not self.is_animating:
            self.cube_tracker.apply_moves([move])  # Update cube state
            self.animate_move(move)

    # IN THE StaticCubeViewer CLASS:

        # In the StaticCubeViewer class:

    def _get_affected_positions(self, move):
        """Dynamically determine positions affected by the move based on current cube layers."""
        move_upper = move.upper()
        axis_map = {
            'U': 1, 'D': 1,  # Y-axis (rows)
            'L': 2, 'R': 2,  # Z-axis (depth)
            'F': 0, 'B': 0   # X-axis (slices)
        }
        layer_map = {
            'U': 0, 'D': 2,
            'L': 0, 'R': 2,
            'F': 2, 'B': 0
        }
        
        axis = axis_map[move_upper]
        layer = layer_map[move_upper]
        
        # Get all positions in the target layer
        positions = []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    pos = (i, j, k)
                    if pos[axis] == layer and pos != (1, 1, 1):
                        positions.append(pos)
        return positions

    def animate_move(self, move):
        """Animate the move based on current cube state."""
        if self.is_animating:
            return

        self.is_animating = True
        angle = 90.0 if move.isupper() else -90.0
        move_upper = move.upper()

        # Get CURRENT affected positions
        affected_positions = self._get_affected_positions(move_upper)
        
        # Get current piece IDs in these positions
        affected_piece_ids = [
            self.cube_tracker.piece_current_ids_at_positions[pos[0], pos[1], pos[2]]
            for pos in affected_positions
        ]
        affected_nodes = [self.piece_id_to_node[pid] for pid in affected_piece_ids]

        # Set rotation axis based on move
        hpr = Vec3(0, 0, 0)
        if move_upper == 'U':
            hpr.setX(-angle)  # Rotate around local Z
        elif move_upper == 'D':
            hpr.setX(angle)
        elif move_upper == 'L':
            hpr.setY(-angle)  # Rotate around local X
        elif move_upper == 'R':
            hpr.setY(angle)
        elif move_upper == 'F':
            hpr.setZ(-angle)  # Rotate around local Y
        elif move_upper == 'B':
            hpr.setZ(angle)

        # Reparent nodes to rotation pivot
        for node in affected_nodes:
            node.wrtReparentTo(self.rotation_pivot)

        # Animate and clean up
        rotate_interval = LerpHprInterval(
            self.rotation_pivot, self.animation_speed, hpr)
        cleanup_interval = Func(self._finish_animation, affected_nodes)
        self.anim_sequence = Sequence(rotate_interval, cleanup_interval)
        self.anim_sequence.start()

    def _finish_animation(self, nodes):
        """Cleanup after animation."""
        for node in nodes:
            node.wrtReparentTo(self.cube_node)
        self.rotation_pivot.setHpr(0, 0, 0)
        self.is_animating = False

    def sleep_task(self, task):
        """Explicitly reduce frame rate to ~30 FPS."""
        time.sleep(0.033)  # ~30 FPS
        return task.cont

    # ... [Rest of the code unchanged from previous answer] ...

if __name__ == "__main__":
    try:
        app = StaticCubeViewer()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)