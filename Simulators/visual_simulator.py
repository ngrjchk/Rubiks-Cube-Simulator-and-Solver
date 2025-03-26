# static_cube_viewer.py (Based on Your Reference + time.sleep)

import sys
import os
import numpy as np
import random
import time # <<< IMPORT time MODULE

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
loadPrcFileData('', 'window-title Standalone Animated Cube')
loadPrcFileData('', 'sync-video #f')         # Keep vsync off
loadPrcFileData('', 'show-frame-rate-meter #t') # Keep FPS meter visible
# --- Clock settings might still help ---
loadPrcFileData('', 'clock-mode limited')
loadPrcFileData('', 'clock-frame-rate 60')


class StaticCubeViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # --- Colors ---
        self.colors = {
            "White":  VBase4(0.9, 0.9, 0.9, 1), "Yellow": VBase4(0.9, 0.9, 0.0, 1),
            "Blue":   VBase4(0.0, 0.0, 0.8, 1), "Green":  VBase4(0.0, 0.6, 0.0, 1),
            "Red":    VBase4(0.8, 0.0, 0.0, 1), "Orange": VBase4(1.0, 0.5, 0.0, 1),
            "Black":  VBase4(0.1, 0.1, 0.1, 1),
        }

        # --- Mappings (From Your Reference) ---
        self.normal_to_solved_color = {
             (1, 0, 0): "Orange",    (-1, 0, 0): "Red",    # Assuming your egg/view has +X=Orange, -X=Red
             (0, 1, 0): "Green",     ( 0,-1, 0): "Blue",   # Assuming +Y=Green, -Y=Blue
             (0, 0, 1): "White",     ( 0, 0,-1): "Yellow", # Assuming +Z=White, -Z=Yellow
        }
        self.normal_to_material_name_map = {
             (-1, 0, 0) : "mat_pos_x", (1, 0, 0) : "mat_neg_x", # Mapping normal to corrected EGG material names
             ( 0,-1, 0) : "mat_pos_y", (0, 1, 0) : "mat_neg_y", # Check if Y mapping matches solved colors above
             ( 0, 0, 1) : "mat_pos_z", (0, 0,-1) : "mat_neg_z",
        }
        # NOTE: There's an apparent mismatch in your normal_to_solved_color (+X=Orange, -X=Red) vs
        # normal_to_material_name_map (+X normal uses mat_neg_x (Orange), -X normal uses mat_pos_x(Red)).
        # This looks correct if your view has Orange on the right (+X) and Red on the left (-X). Please verify!
        # Same applies potentially to Y axis (Green/Blue).

        self.cubie_nodes = {}

        # --- Scene Setup ---
        self.disableMouse(); self.camera.setPos(0, -15, 3); self.camera.lookAt(0, 0, 0); self.setBackgroundColor(0.2, 0.2, 0.2)

        # --- Lighting (Ambient Only - Strong) ---
        alight = AmbientLight('ambient_light')
        alight.setColor((1.0, 1.0, 1.0, 1.0))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        # --- Load Cubie Model ---
        try:
            self.cubie_model = self.loader.loadModel("models/cube.egg") # Assumes corrected EGG
            if not self.cubie_model: raise IOError("Model not loaded")
        except Exception as e:
            print(f"FATAL: Could not load model 'models/cube.egg': {e}")
            sys.exit()

        # --- Build Visual Representation ---
        self.cube_node = self.render.attachNewNode("cube_pivot")
        self.rotation_pivot = self.render.attachNewNode("rotation_pivot")
        self._build_static_cube()

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


        # --- *** ADD SLEEP TASK *** ---
        self.taskMgr.add(self.sleep_task, "sleepTask")
        # --- *** END ADD SLEEP TASK *** ---


        print("-" * 30); print("Standalone Animated Cube Viewer Initialized (FPS Limited - Sleep)."); print("Controls:"); print("  Mouse Click+Drag: Rotate cube view"); print("  U/D/L/R/F/B Keys (Shift=Inv): Animate move"); print("  Escape: Exit"); print("-" * 30)

        # --- Animation State ---
        self.is_animating = False
        self.animation_speed = 0.25

    # --- *** Task for Sleeping *** ---
    def sleep_task(self, task):
        """Explicitly sleep for a short duration each frame to limit CPU."""
        sleep_duration = 0.05 # Sleep for 50 milliseconds (Adjust for ~target FPS)
        time.sleep(sleep_duration)
        return task.cont # Continue the task indefinitely
    # --- *** End Task for Sleeping *** ---

    # --- Mouse Drag ---
    def start_drag(self):
        if self.mouseWatcherNode.hasMouse(): self.dragging = True; self.last_mouse_x = self.mouseWatcherNode.getMouseX(); self.last_mouse_y = self.mouseWatcherNode.getMouseY()
    def stop_drag(self): self.dragging = False
    def drag_cube_task(self, task):
        if self.dragging and self.mouseWatcherNode.hasMouse():
            mx = self.mouseWatcherNode.getMouseX(); my = self.mouseWatcherNode.getMouseY()
            dx = mx - self.last_mouse_x; dy = my - self.last_mouse_y
            self.cube_node.setH(self.cube_node.getH() + dx * 180)
            self.cube_node.setP(self.cube_node.getP() - dy * 180)
            self.last_mouse_x = mx; self.last_mouse_y = my
        return task.cont

    # --- Positioning ---
    def _get_panda_pos(self, i, j, k):
        scale = 1.02; offset = 1.0
        panda_x = (k - offset) * scale; panda_y = (offset - i) * scale; panda_z = (offset - j) * scale
        return Point3(panda_x, panda_y, panda_z)

    # --- Build and Color Static Cube ---
    def _build_static_cube(self):
        """Creates, places, and colors the static solved cube."""
        # print("--- Building Static Cube ---") # Less verbose
        center_indices = (1, 1, 1); built_count = 0
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    current_pos_indices = (i, j, k)
                    if current_pos_indices == center_indices: continue
                    cubie_panda_pos = self._get_panda_pos(i, j, k)
                    cubie_node = self.render.attachNewNode(f"cubie_geom_{i}_{j}_{k}")
                    instance = self.cubie_model.copyTo(cubie_node)
                    cubie_node.reparentTo(self.cube_node)
                    cubie_node.setPos(cubie_panda_pos)
                    for normal_vec, material_name in self.normal_to_material_name_map.items():
                        mat = cubie_node.findMaterial(material_name)
                        if mat:
                            is_outer_face = False
                            if abs(normal_vec[0]) > 0.5 and k in [0, 2]: is_outer_face = True
                            if abs(normal_vec[1]) > 0.5 and i in [0, 2]: is_outer_face = True
                            if abs(normal_vec[2]) > 0.5 and j in [0, 2]: is_outer_face = True
                            color_name = self.normal_to_solved_color.get(normal_vec, "Black") if is_outer_face else "Black"
                            color_vec4 = self.colors.get(color_name, self.colors["Black"])
                            mat.setAmbient(color_vec4); mat.setDiffuse(color_vec4) # Set ambient=diffuse
                            mat.setSpecular((0, 0, 0, 1)); mat.setShininess(0.0); mat.setEmission((0,0,0,1))
                    self.cubie_nodes[current_pos_indices] = cubie_node
                    built_count += 1
        # print(f"--- Finished building static cube - Built {built_count} nodes ---") # Less verbose

    # --- Animation Methods ---
    def get_affected_cubie_indices_for_animation(self, move):
        indices = []; move_upper = move.upper(); center_idx = (1,1,1)
        if   move_upper == 'U': layer_idx = 0; axis_idx = 1 # j=0
        elif move_upper == 'D': layer_idx = 2; axis_idx = 1 # j=2
        elif move_upper == 'L': layer_idx = 0; axis_idx = 2 # k=0
        elif move_upper == 'R': layer_idx = 2; axis_idx = 2 # k=2
        elif move_upper == 'B': layer_idx = 0; axis_idx = 0
        elif move_upper == 'F': layer_idx = 2; axis_idx = 0 
         
        else: return []
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    idx_tuple = (i,j,k)
                    if idx_tuple != center_idx and idx_tuple[axis_idx] == layer_idx:
                        indices.append(idx_tuple)
        return indices

    def animate_move(self, move):
        if self.is_animating: return # Don't overlap
        self.is_animating = True
        angle = 90.0; hpr = Vec3(0,0,0)
        if move.islower(): angle = -90.0
        move_upper = move.upper()
        # Rotation based on Panda Axes (Z-up, Y-forward, X-right)
        if   move_upper == 'U': hpr.setX(angle)    # Around Z
        elif move_upper == 'D': hpr.setX(-angle)
        elif move_upper == 'L': hpr.setY(angle)    # Around X
        elif move_upper == 'R': hpr.setY(-angle)
        elif move_upper == 'F': hpr.setZ(-angle)   # Around Y (Front CW is neg rot around +Y)
        elif move_upper == 'B': hpr.setZ(angle)    # Around Y (Back CW is pos rot around +Y)
        else: self.is_animating = False; return

        affected_initial_indices = self.get_affected_cubie_indices_for_animation(move)
        affected_nodes = []
        for initial_idx in affected_initial_indices:
             if initial_idx in self.cubie_nodes:
                node = self.cubie_nodes[initial_idx]
                node.wrtReparentTo(self.rotation_pivot)
                affected_nodes.append(node)
        if not affected_nodes: self.is_animating = False; return

        rotate_interval = LerpHprInterval(self.rotation_pivot, duration=self.animation_speed, hpr=hpr, startHpr=Vec3(0,0,0))
        cleanup_interval = Func(self._animation_cleanup_standalone, affected_nodes, move)
        self.anim_sequence = Sequence(rotate_interval, cleanup_interval, name=f"anim-{move}")
        self.anim_sequence.start()

    def _animation_cleanup_standalone(self, affected_nodes, move):
        for node in affected_nodes: node.wrtReparentTo(self.cube_node)
        self.rotation_pivot.setHpr(0, 0, 0)
        # print(f"Finished animation for: {move}") # Optional
        self.is_animating = False

    def trigger_animation(self, move):
        if not self.is_animating: self.animate_move(move)
        # else: print("Animation in progress...")


# --- Main Execution Logic ---
if __name__ == "__main__":
    try:
        app = StaticCubeViewer()
        app.run()
    except Exception as e:
        print("\n--- AN ERROR OCCURRED ---"); import traceback; traceback.print_exc(); print("--- END ERROR ---")
