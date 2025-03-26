# static_cube_viewer.py (Correct LOCAL Rotation Pivot)

import sys
import os
import numpy as np
import random
import time

# --- Panda3D Imports ---
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    NodePath, Point3, Vec3, VBase4, Material,
    AmbientLight,
    loadPrcFileData
)
# --- Interval Imports ---
from direct.interval.IntervalGlobal import Sequence, LerpHprInterval, Func, Wait

# --- Panda3D Config ---
loadPrcFileData('', 'window-title Standalone Animated Cube (Local Rot)')
loadPrcFileData('', 'sync-video #f')
loadPrcFileData('', 'show-frame-rate-meter #t')
loadPrcFileData('', 'clock-mode limited')
loadPrcFileData('', 'clock-frame-rate 60')

class StaticCubeViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # --- Colors & Mappings (Using YOUR confirmed scheme) ---
        self.colors = { "White": VBase4(0.9, 0.9, 0.9, 1), "Yellow": VBase4(0.9, 0.9, 0.0, 1), "Blue": VBase4(0.0, 0.0, 0.8, 1), "Green": VBase4(0.0, 0.6, 0.0, 1), "Red": VBase4(0.8, 0.0, 0.0, 1), "Orange": VBase4(1.0, 0.5, 0.0, 1), "Black": VBase4(0.1, 0.1, 0.1, 1), }
        self.normal_to_solved_color = { (1, 0, 0): "Orange", (-1, 0, 0): "Red", (0, 1, 0): "Green", (0,-1, 0): "Blue", (0, 0, 1): "White", (0, 0,-1): "Yellow", }
        self.normal_to_material_name_map = { (1, 0, 0): "mat_neg_x", (-1, 0, 0): "mat_pos_x", (0, 1, 0): "mat_pos_y", (0,-1, 0): "mat_neg_y", (0, 0, 1): "mat_pos_z", (0, 0,-1): "mat_neg_z" } # Matched EGG to your colors

        self.cubie_nodes = {}

        # --- Scene Setup ---
        self.disableMouse(); self.camera.setPos(0, -15, 3); self.camera.lookAt(0, 0, 0); self.setBackgroundColor(0.2, 0.2, 0.2)
        # --- Lighting ---
        alight = AmbientLight('ambient_light'); alight.setColor((1.0, 1.0, 1.0, 1.0)); alnp = self.render.attachNewNode(alight); self.render.setLight(alnp)

        # --- Load Cubie Model ---
        try:
            self.cubie_model = self.loader.loadModel("models/cube.egg") # Assumes YOUR corrected EGG
            if not self.cubie_model: raise IOError("Model not loaded")
        except Exception as e: print(f"FATAL: Could not load model: {e}"); sys.exit()

        # --- Build Visual Representation ---
        self.cube_node = self.render.attachNewNode("cube_pivot") # Main draggable node
        # --- *** rotation_pivot is CHILD of cube_node *** ---
        self.rotation_pivot = self.cube_node.attachNewNode("rotation_pivot")
        # --- *** ---
        self._build_static_cube() # Build geometry, parent cubies to cube_node

        # --- Interaction ---
        self.accept('mouse1', self.start_drag); self.accept('mouse1-up', self.stop_drag); self.taskMgr.add(self.drag_cube_task, "dragCubeTask")
        self.dragging = False; self.last_mouse_x = 0; self.last_mouse_y = 0
        self.accept('escape', sys.exit)
        self.accept('u', self.trigger_animation, ['U']); self.accept('shift-u', self.trigger_animation, ['u'])
        self.accept('r', self.trigger_animation, ['R']); self.accept('shift-r', self.trigger_animation, ['r'])
        self.accept('l', self.trigger_animation, ['L']); self.accept('shift-l', self.trigger_animation, ['l'])
        self.accept('f', self.trigger_animation, ['F']); self.accept('shift-f', self.trigger_animation, ['f'])
        self.accept('b', self.trigger_animation, ['B']); self.accept('shift-b', self.trigger_animation, ['b'])
        self.accept('d', self.trigger_animation, ['D']); self.accept('shift-d', self.trigger_animation, ['d'])

        # --- FPS Limiting Task ---
        self.taskMgr.add(self.sleep_task, "sleepTask")

        print("-" * 30); print("Standalone Animated Cube Viewer Initialized (Local Rotation)."); # ... print controls ...; print("-" * 30)
        self.is_animating = False; self.animation_speed = 0.25

    # --- Task for Sleeping ---
    def sleep_task(self, task):
        sleep_duration = 0.005; time.sleep(sleep_duration)
        return task.cont

    # --- Mouse Drag ---
    def start_drag(self): # Keep as before
        if self.mouseWatcherNode.hasMouse(): self.dragging = True; self.last_mouse_x = self.mouseWatcherNode.getMouseX(); self.last_mouse_y = self.mouseWatcherNode.getMouseY()
    def stop_drag(self): self.dragging = False # Keep as before
    def drag_cube_task(self, task): # Keep as before
        if self.dragging and self.mouseWatcherNode.hasMouse():
            mx = self.mouseWatcherNode.getMouseX(); my = self.mouseWatcherNode.getMouseY()
            dx = mx - self.last_mouse_x; dy = my - self.last_mouse_y
            self.cube_node.setH(self.cube_node.getH() + dx * 180)
            self.cube_node.setP(self.cube_node.getP() - dy * 180)
            self.last_mouse_x = mx; self.last_mouse_y = my
        return task.cont

    # --- Positioning ---
    def _get_panda_pos(self, i, j, k): # Keep as before
        scale = 1.02; offset = 1.0
        panda_x = (k - offset) * scale; panda_y = (offset - i) * scale; panda_z = (offset - j) * scale
        return Point3(panda_x, panda_y, panda_z)

    # --- Build and Color Static Cube ---
    def _build_static_cube(self): # Keep corrected version with internal face coloring
        center_indices = (1, 1, 1); built_count = 0
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    current_pos_indices = (i, j, k)
                    if current_pos_indices == center_indices: continue
                    cubie_panda_pos = self._get_panda_pos(i, j, k)
                    cubie_node = self.render.attachNewNode(f"cubie_geom_{i}_{j}_{k}")
                    instance = self.cubie_model.copyTo(cubie_node)
                    cubie_node.reparentTo(self.cube_node) # Cubies are children of cube_node
                    cubie_node.setPos(cubie_panda_pos)
                    # Apply solved colors, blacking out internal faces
                    for normal_vec, material_name in self.normal_to_material_name_map.items():
                        mat = cubie_node.findMaterial(material_name)
                        if mat:
                            is_outer_face = False
                            if abs(normal_vec[0]) > 0.5 and k in [0, 2]: is_outer_face = True
                            if abs(normal_vec[1]) > 0.5 and i in [0, 2]: is_outer_face = True
                            if abs(normal_vec[2]) > 0.5 and j in [0, 2]: is_outer_face = True
                            color_name = self.normal_to_solved_color.get(normal_vec, "Black") if is_outer_face else "Black"
                            color_vec4 = self.colors.get(color_name, self.colors["Black"])
                            mat.setAmbient(color_vec4*0.8 if color_name != "Black" else color_vec4*0.1); mat.setDiffuse(color_vec4)
                            mat.setSpecular((0,0,0,1)); mat.setShininess(0.0); mat.setEmission((0,0,0,1))
                    self.cubie_nodes[current_pos_indices] = cubie_node
                    built_count += 1

    # --- Animation Methods ---
    def get_affected_cubie_indices_for_animation(self, move): # Use YOUR layer/axis indices
        indices = []; move_upper = move.upper(); center_idx = (1,1,1)
        if   move_upper == 'U': layer_idx = 0; axis_idx = 1
        elif move_upper == 'D': layer_idx = 2; axis_idx = 1
        elif move_upper == 'L': layer_idx = 0; axis_idx = 2
        elif move_upper == 'R': layer_idx = 2; axis_idx = 2
        elif move_upper == 'F': layer_idx = 2; axis_idx = 0 # YOUR i=2 for F
        elif move_upper == 'B': layer_idx = 0; axis_idx = 0 # YOUR i=0 for B
        else: return []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    idx_tuple = (i,j,k)
                    if all(0 <= coord <= 2 for coord in idx_tuple):
                         if idx_tuple != center_idx and idx_tuple[axis_idx] == layer_idx:
                            indices.append(idx_tuple)
        return indices

    def animate_move(self, move):
        if self.is_animating: return
        self.is_animating = True
        angle = 90.0; hpr = Vec3(0,0,0)
        if move.islower(): angle = -90.0
        move_upper = move.upper()
        # Use YOUR HPR mapping relative to the LOCAL pivot
        if   move_upper == 'U': hpr.setZ(angle)    # YOURS: Around Z (Heading)
        elif move_upper == 'D': hpr.setZ(-angle)
        elif move_upper == 'L': hpr.setX(angle)    # YOURS: Around X (Pitch)
        elif move_upper == 'R': hpr.setX(-angle)
        elif move_upper == 'F': hpr.setY(-angle)   # YOURS: Around Y (Roll)
        elif move_upper == 'B': hpr.setY(angle)
        else: self.is_animating = False; return

        affected_initial_indices = self.get_affected_cubie_indices_for_animation(move)
        affected_nodes = []
        if not affected_initial_indices: self.is_animating = False; return

        # Ensure the LOCAL rotation pivot is at the origin *relative to its parent (cube_node)*
        self.rotation_pivot.setPosHpr(0,0,0,0,0,0)

        # Reparent affected nodes to the LOCAL pivot
        for initial_idx in affected_initial_indices:
             if initial_idx in self.cubie_nodes:
                node = self.cubie_nodes[initial_idx]
                # --- *** Use simple reparentTo LOCAL pivot *** ---
                node.reparentTo(self.rotation_pivot)
                # --- *** ---
                affected_nodes.append(node)

        if not affected_nodes: self.is_animating = False; return # Check again after trying to reparent

        # Animate the HPR of the LOCAL rotation_pivot
        rotate_interval = LerpHprInterval(self.rotation_pivot,
                                          duration=self.animation_speed,
                                          hpr=hpr, # Target rotation change
                                          startHpr=Vec3(0,0,0)) # Start from non-rotated state

        cleanup_interval = Func(self._animation_cleanup_standalone, affected_nodes, move)
        self.anim_sequence = Sequence(rotate_interval, cleanup_interval, name=f"anim-{move}")
        self.anim_sequence.start()

    def _animation_cleanup_standalone(self, affected_nodes, move):
        parent_node = self.cube_node # Parent to return to
        for node in affected_nodes:
             if not node.isEmpty():
                  # --- *** Use simple reparentTo cube_node *** ---
                  node.reparentTo(parent_node)
                  # --- *** ---
        # We don't need to reset the local pivot's HPR here, LerpHprInterval starts from 0

        # No state update in standalone
        self.is_animating = False

    def trigger_animation(self, move):
        if not self.is_animating: self.animate_move(move)

# --- Main Execution Logic ---
if __name__ == "__main__":
    try:
        app = StaticCubeViewer()
        app.run()
    except Exception as e:
        print("\n--- AN ERROR OCCURRED ---"); import traceback; traceback.print_exc(); print("--- END ERROR ---")
        input("Press Enter to exit...")