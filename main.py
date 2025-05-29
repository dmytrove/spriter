import json
import math
import os
import random
from pathlib import Path
from ursina import *
from ursina.vec3 import Vec3
# Import shader strings from shaders.py
import shaders 

# --- Constants and Configuration ---
DEFAULT_EMOJI_SET = "noto_emoji_regular.json"
DEFAULT_EMOJI_GROUP = "Smileys & Emotion"
DEFAULT_RESOLUTION_FOLDER = "128"
EMOJI_ASSET_BASE_PATH = Path("assets/noto-emoji/png/")
EMOJI_SET_BASE_PATH = Path("assets/sets/")

# --- Texture Cache ---
texture_cache = {}

class EmojiApp(Ursina):
    def __init__(self):
        super().__init__()

        self.scene.clear()
        camera.fov = 75
        camera.position = (0, 1, -15)
        camera.look_at(Vec3(0,0,0))
        camera.clip_plane_near = 0.1
        camera.clip_plane_far = 1000

        self.sprites = []
        self.num_sprites = 30
        
        # Animation Parameters (as before)
        self.idle_rotation_enabled = True
        self.idle_zoom_enabled = True
        self.idle_rotation_pattern = 'sin' 
        self.idle_zoom_pattern = 'sin'     
        self.idle_rotation_speed = 30      
        self.idle_zoom_amplitude = 0.1     
        self.idle_zoom_speed_factor = 2.0

        self.node_animation_enabled = True
        self.node_animation_type = 'wave_position' 
        self.node_anim_amplitude = 0.5
        self.node_anim_frequency = 1.0
        self.node_anim_speed = 1.0
        
        self.current_arrangement = 'sphere'

        # Post-Processing Parameters
        self.grayscale_enabled = False
        self.sepia_enabled = False
        self.sepia_amount = 1.0
        self.bloom_enabled = False # Conceptual
        self.afterimage_enabled = False # Conceptual
        self.afterimage_damp = 0.85

        self.custom_shaders = {}
        self.load_custom_shaders()

        self.load_and_arrange_emojis()
        self.setup_sprite_initial_states()

    def load_custom_shaders(self):
        """Load and compile custom GLSL shaders."""
        self.custom_shaders['grayscale'] = Shader(
            vertex=shaders.grayscale_shader_vert,
            fragment=shaders.grayscale_shader_frag,
            name='grayscale_shader' 
        )
        self.custom_shaders['sepia'] = Shader(
            vertex=shaders.sepia_shader_vert,
            fragment=shaders.sepia_shader_frag,
            name='sepia_shader'
        )
        # Conceptual shaders (not fully implemented for rendering due to multi-pass complexity)
        print("Conceptual Bloom and Afterimage shaders loaded in principle, but not fully hooked into rendering pipeline.")


    def setup_sprite_initial_states(self):
        for i, sprite in enumerate(self.sprites):
            if not hasattr(sprite, 'base_scale_val'): # Store scalar base for uniform scaling
                 sprite.base_scale_val = sprite.scale_x if sprite.scale_x == sprite.scale_y else max(sprite.scale_x, sprite.scale_y)

            sprite.base_scale = Vec3(sprite.scale_x, sprite.scale_y, sprite.scale_z) # Keep Vec3 for potential non-uniform
            sprite.base_position = Vec3(sprite.x, sprite.y, sprite.z)
            sprite.base_rotation_z = sprite.world_rotation_z 
            sprite.animation_phase_offset = random.uniform(0, 2 * math.pi)


    def load_emoji_texture(self, emoji_codepoint_filename, resolution_folder=DEFAULT_RESOLUTION_FOLDER):
        texture_path_str = str(EMOJI_ASSET_BASE_PATH / resolution_folder / emoji_codepoint_filename)
        if texture_path_str in texture_cache:
            return texture_cache[texture_path_str]
        
        if Path(texture_path_str).exists():
            texture_cache[texture_path_str] = texture_path_str
            return texture_path_str
        else:
            print(f"Warning: Texture {texture_path_str} not found.")
            return None


    def get_emoji_filenames_for_set_and_group(self, set_filename, group_name):
        set_file_path = EMOJI_SET_BASE_PATH / set_filename
        try:
            with open(set_file_path, 'r', encoding='utf-8') as f: data = json.load(f)
            emoji_chars = []
            if isinstance(data, dict):
                emoji_chars = data.get(group_name, [])
                if isinstance(emoji_chars, str): emoji_chars = [e.strip() for e in emoji_chars.split(';') if e.strip()]
            elif isinstance(data, list): emoji_chars = data
            if not emoji_chars: return []
            return [f"emoji_u{'_'.join(c.encode('unicode_escape').decode('utf-8').split('U')[-1].lstrip('0').lower() for c in char if c)}.png" for char in emoji_chars if char]
        except FileNotFoundError: print(f"Error: Set file {set_file_path} not found."); return []
        except json.JSONDecodeError: print(f"Error: JSON decode error for {set_file_path}."); return []

    def create_emoji_sprite(self, texture_path_or_object):
        if not texture_path_or_object:
            return Entity(model='quad', color=color.red, scale=1, name="fallback_sprite")
        sprite = Entity(model='quad', texture=texture_path_or_object, scale=1, billboard=True, double_sided=True)
        sprite.base_scale_val = 1.0 
        sprite.base_scale = Vec3(1,1,1)
        sprite.base_position = Vec3(0,0,0) 
        sprite.base_rotation_z = 0 
        sprite.animation_phase_offset = random.uniform(0, 2 * math.pi)
        return sprite

    def _apply_arrangement_and_setup_state(self, arrangement_name, active_sprites, callback, *args):
        callback(active_sprites, *args)
        self.current_arrangement = arrangement_name
        self.setup_sprite_initial_states() # Crucial: update base states after arrangement

    def arrange_sprites_grid(self, sprites_to_arrange, num_cols, num_rows, cell_size, emoji_scale_val):
        idx = 0
        for r in range(num_rows):
            for c in range(num_cols):
                if idx < len(sprites_to_arrange):
                    sprite = sprites_to_arrange[idx]
                    sprite.base_scale_val = emoji_scale_val
                    sprite.scale = emoji_scale_val # Uniform scale
                    sprite.base_position = Vec3((c - num_cols/2 + 0.5)*cell_size, (r - num_rows/2 + 0.5)*cell_size, 0)
                    sprite.position = sprite.base_position
                    sprite.visible = True; sprite.billboard = True; sprite.rotation = (0,0,0)
                    idx += 1
                else: break
            else: continue
            break
        for i in range(idx, len(sprites_to_arrange)): sprites_to_arrange[i].visible = False

    def _arrange_3d_pattern(self, sprite, pos_vec, scale_val, look_at_target_vec):
        sprite.base_scale_val = scale_val
        sprite.scale = scale_val # Uniform scale
        sprite.base_position = pos_vec
        sprite.position = sprite.base_position
        sprite.billboard = False
        sprite.look_at(look_at_target_vec, axis='up')
        sprite.rotation_x += 90 
        sprite.visible = True

    def arrange_sprites_swirl(self, sprites_to_arrange, num_sprites_in_pattern, turns, radius, height_factor, emoji_scale_val):
        for i, sprite in enumerate(sprites_to_arrange):
            if i < num_sprites_in_pattern:
                t = i / max(1, num_sprites_in_pattern -1); angle = t * turns * 2 * math.pi
                pos = Vec3(radius*math.cos(angle), (t-0.5)*height_factor, radius*math.sin(angle))
                self._arrange_3d_pattern(sprite, pos, emoji_scale_val, pos + Vec3(pos.x,0,pos.z).normalized())
            else: sprite.visible = False

    def arrange_sprites_torus(self, sprites_to_arrange, num_sprites_in_pattern, R, r_minor, emoji_scale_val):
        for i, sprite in enumerate(sprites_to_arrange):
            if i < num_sprites_in_pattern:
                u = (i/num_sprites_in_pattern)*2*math.pi; v = (i*(2*math.pi*5/num_sprites_in_pattern))
                pos = Vec3((R+r_minor*math.cos(v))*math.cos(u), r_minor*math.sin(v), (R+r_minor*math.cos(v))*math.sin(u))
                normal = Vec3(math.cos(u)*math.cos(v), math.sin(v), math.sin(u)*math.cos(v)).normalized()
                self._arrange_3d_pattern(sprite, pos, emoji_scale_val, pos + normal)
            else: sprite.visible = False

    def arrange_sprites_sphere(self, sprites_to_arrange, num_sprites_in_pattern, sphere_r, emoji_scale_val):
        phi = math.pi * (math.sqrt(5.) - 1.)
        for i, sprite in enumerate(sprites_to_arrange):
            if i < num_sprites_in_pattern:
                y_s = 1-(i/float(max(1,num_sprites_in_pattern-1)))*2; r_s = math.sqrt(max(0,1-y_s*y_s))
                theta = phi*i; x_s = math.cos(theta)*r_s; z_s = math.sin(theta)*r_s
                pos = Vec3(x_s,y_s,z_s) * sphere_r
                self._arrange_3d_pattern(sprite, pos, emoji_scale_val, pos + Vec3(x_s,y_s,z_s).normalized())
            else: sprite.visible = False
    
    def load_and_arrange_emojis(self):
        filenames = self.get_emoji_filenames_for_set_and_group(DEFAULT_EMOJI_SET, DEFAULT_EMOJI_GROUP)
        if not filenames:
            if not self.sprites: self.sprites.append(Entity(model='quad',color=color.red,scale=1, name="fallback_sprite"))
            return

        for i in range(self.num_sprites):
            filename = filenames[i % len(filenames)]
            texture_ref = self.load_emoji_texture(filename, DEFAULT_RESOLUTION_FOLDER)
            if i < len(self.sprites):
                sprite = self.sprites[i]
                sprite.texture = texture_ref if texture_ref else "white_cube" # Ursina's default fallback
                sprite.color = color.white if texture_ref else color.red
                sprite.visible = True
            else:
                sprite = self.create_emoji_sprite(texture_ref)
                self.sprites.append(sprite)
        
        for i in range(self.num_sprites, len(self.sprites)): self.sprites[i].visible = False
        
        active_sprites = self.sprites[:self.num_sprites]
        arrangement_map = {
            'grid': (self.arrange_sprites_grid, 5, math.ceil(self.num_sprites/5), 1.2, 1),
            'swirl': (self.arrange_sprites_swirl, self.num_sprites, 3, 3, 5, 0.7),
            'torus': (self.arrange_sprites_torus, self.num_sprites, 3, 1, 0.5),
            'sphere': (self.arrange_sprites_sphere, self.num_sprites, 3, 0.6)
        }
        if self.current_arrangement in arrangement_map:
            func, *args = arrangement_map[self.current_arrangement]
            self._apply_arrangement_and_setup_state(self.current_arrangement, active_sprites, func, *args)


    def input(self, key):
        super().input(key)
        arrangement_args_map = {
            '1': ('grid', 5, math.ceil(self.num_sprites/5), 1.2, 1),
            '2': ('swirl', self.num_sprites, 3, 3, 5, 0.7),
            '3': ('torus', self.num_sprites, 3, 1, 0.5),
            '4': ('sphere', self.num_sprites, 3, 0.6)
        }
        if key in arrangement_args_map:
            name, *args = arrangement_args_map[key]
            arrange_func = getattr(self, f"arrange_sprites_{name}")
            self._apply_arrangement_and_setup_state(name, self.sprites[:self.num_sprites], arrange_func, *args)
        
        elif key == 'r': self.idle_rotation_enabled = not self.idle_rotation_enabled
        elif key == 't': self.idle_zoom_enabled = not self.idle_zoom_enabled
        elif key == 'n': # Cycle node animations
            patterns = ['none', 'wave_position', 'wave_zoom', 'wave_rotation']
            current_idx = patterns.index(self.node_animation_type)
            self.node_animation_type = patterns[(current_idx + 1) % len(patterns)]
        
        # Post-processing toggles
        elif key == 'g': self.grayscale_enabled = not self.grayscale_enabled; self.apply_post_processing()
        elif key == 's': self.sepia_enabled = not self.sepia_enabled; self.apply_post_processing()
        elif key == 'b': self.bloom_enabled = not self.bloom_enabled; print(f"Conceptual Bloom: {'On' if self.bloom_enabled else 'Off'}") # Conceptual toggle
        elif key == 'a': self.afterimage_enabled = not self.afterimage_enabled; print(f"Conceptual Afterimage: {'On' if self.afterimage_enabled else 'Off'}") # Conceptual toggle
        elif key == 's up': self.sepia_amount = min(1.0, self.sepia_amount + 0.1); self.apply_post_processing()
        elif key == 's down': self.sepia_amount = max(0.0, self.sepia_amount - 0.1); self.apply_post_processing()
        elif key == 'escape': application.quit()

    def apply_post_processing(self):
        # Ursina applies shaders in the order they are set if using camera.shader directly.
        # For multiple effects, a more robust pipeline (e.g. chaining render buffers) is needed.
        # Here, we'll just allow one simple effect at a time or let Ursina handle it if it implicitly chains.
        
        # Reset shader first
        camera.shader = None 
        
        if self.grayscale_enabled:
            camera.shader = self.custom_shaders['grayscale']
            print("Grayscale shader applied.")
        elif self.sepia_enabled: # Prioritize Sepia if both somehow enabled
            camera.shader = self.custom_shaders['sepia']
            camera.set_shader_input('amount', self.sepia_amount)
            print(f"Sepia shader applied with amount: {self.sepia_amount:.1f}")
        
        # Conceptual Bloom & Afterimage - how they would be managed (if pipeline supported easily)
        # if self.bloom_enabled: 
        #     # This would involve a multi-pass shader setup not directly settable via camera.shader
        #     print("Bloom would be applied here (conceptual).")
        # if self.afterimage_enabled:
        #     # This would involve ping-pong buffers and blending previous frames
        #     print("Afterimage would be applied here (conceptual).")


    def apply_idle_animations(self, sprite, t):
        if self.idle_rotation_enabled:
            factor = 1.0; pattern = self.idle_rotation_pattern
            if pattern == 'sin': factor = math.sin(t*self.idle_zoom_speed_factor + sprite.animation_phase_offset)
            elif pattern == 'pulse': factor = abs(math.sin(t*self.idle_zoom_speed_factor + sprite.animation_phase_offset))
            elif pattern == 'ramp': factor = (math.sin(t*self.idle_zoom_speed_factor + sprite.animation_phase_offset)+1)/2.0
            if sprite.billboard: sprite.world_rotation_z += self.idle_rotation_speed * factor * time.dt
            else: sprite.rotation_y += self.idle_rotation_speed * factor * time.dt

        if self.idle_zoom_enabled and hasattr(sprite, 'base_scale_val'):
            zoom_val = 1.0; pattern = self.idle_zoom_pattern
            if pattern == 'sin': zoom_val = 1.0 + self.idle_zoom_amplitude * math.sin(t*self.idle_zoom_speed_factor*1.5 + sprite.animation_phase_offset)
            elif pattern == 'pulse': zoom_val = 1.0 + self.idle_zoom_amplitude * abs(math.sin(t*self.idle_zoom_speed_factor*1.5 + sprite.animation_phase_offset))
            elif pattern == 'ramp': zoom_val = 1.0 + self.idle_zoom_amplitude * ((math.sin(t*self.idle_zoom_speed_factor*1.5 + sprite.animation_phase_offset)+1)/2.0)
            new_scale = sprite.base_scale_val * zoom_val
            sprite.scale = (new_scale, new_scale, new_scale if not sprite.billboard else sprite.base_scale.z)


    def apply_node_animations(self, sprite, index, t):
        # Reset to base before applying node animation for this frame
        sprite.position = sprite.base_position
        sprite.scale = sprite.base_scale_val # Reset to base scale before node zoom

        if not self.node_animation_enabled or self.node_animation_type == 'none': return

        wave = math.sin(index*self.node_anim_frequency + t*self.node_anim_speed*2.0 + sprite.animation_phase_offset) * self.node_anim_amplitude

        if self.node_animation_type == 'wave_position':
            offset = Vec3(wave, math.cos(index*self.node_anim_frequency*0.7 + t*self.node_anim_speed*1.5 + sprite.animation_phase_offset)*self.node_anim_amplitude, 0)
            sprite.position = sprite.base_position + offset
        
        elif self.node_animation_type == 'wave_zoom':
            scale_factor = 1.0 + wave * 0.5 # Modulate amplitude for zoom
            clamped_scale = max(0.1, scale_factor)
            new_s = sprite.base_scale_val * clamped_scale
            sprite.scale = (new_s, new_s, new_s if not sprite.billboard else sprite.base_scale.z)
            
        elif self.node_animation_type == 'wave_rotation':
            if sprite.billboard: sprite.world_rotation_z += wave * 30 * time.dt 
            else: sprite.rotation_y += wave * 30 * time.dt


    def update(self):
        t = time.time()
        for i, sprite in enumerate(self.sprites):
            if not sprite.visible: continue
            
            # Apply node animations first - they modify position/scale/rotation from base
            self.apply_node_animations(sprite, i, t)
            
            # Then apply idle animations - they further modify the current state
            self.apply_idle_animations(sprite, t)

        if self.current_arrangement in ['swirl', 'torus', 'sphere']:
             camera.rotation_y += time.dt * 7


    # --- Research/Shader Sourcing Description (as per subtask) ---
    def conceptual_shader_sourcing_info(self):
        info = """
        Research/Shader Sourcing for Panda3D/Ursina:

        1. Panda3D Shader Documentation:
           The official Panda3D manual is the primary source. It explains how to write
           and apply GLSL shaders, use shader inputs (uniforms), and manage textures.
           It also covers render-to-texture techniques essential for multi-pass effects.

        2. Panda3D Community Forums:
           The forums are a valuable resource for examples, discussions, and solutions
           to common shader problems. Users often share shader code snippets or entire systems.

        3. Adapting from Online GLSL Resources:
           - ShaderToy: A vast collection of user-created shaders. While many are complex
             and might not directly map to game engine use, the underlying algorithms for
             effects (blur, bloom components, color manipulation) can be adapted.
             Key is understanding the uniforms ShaderToy provides (like iResolution, iTime,
             iChannelN) and mapping them to Panda3D/Ursina equivalents (window dimensions,
             time, texture samplers).
           - GLSL Sandbox, other WebGL sites: Similar to ShaderToy.
           - Graphics programming books/tutorials (e.g., LearnOpenGL.com): Provide
             foundational knowledge and GLSL examples for various effects.

        4. Ursina's Built-in Shaders & Customization:
           Ursina provides some default shaders (e.g., lit, unlit, basic post-processing
           like screen_greyscale). Examining their source (if accessible or by experimentation)
           can give clues on how Ursina handles shader inputs and its rendering pipeline.
           Custom shaders in Ursina are instances of the `Shader` class.

        Process for Bloom/Afterimage:
        - Bloom: Requires multiple passes:
            a) Render scene to texture A.
            b) Brightness pass: Read texture A, output bright areas to texture B.
            c) Blur pass(es): Read texture B, apply horizontal blur to texture C.
                               Read texture C, apply vertical blur to texture B (ping-pong).
                               Repeat blur for smoother results.
            d) Composite pass: Read original scene (texture A) and final blurred brights
                               (texture B), add/screen blend them to the framebuffer.
        - Afterimage: Requires storing the previous frame's result.
            a) Render current scene to texture `current_f`.
            b) Composite pass: Blend `current_f` with `previous_f` (texture from last step)
                               into a new texture `new_previous_f` (or directly to screen).
            c) `previous_f` becomes `new_previous_f`. This is often done with ping-pong buffers.
           This typically requires managing Frame Buffer Objects (FBOs) and texture attachments,
           which is a Panda3D-level concern. Ursina's `camera.shader` is simpler and might
           not directly support easy FBO ping-ponging for custom shaders without more work.
           Ursina's internal post-processing effects likely do this under the hood.
        """
        print(info)

if __name__ == '__main__':
    # Dummy asset creation (as before)
    (EMOJI_ASSET_BASE_PATH / DEFAULT_RESOLUTION_FOLDER).mkdir(parents=True, exist_ok=True)
    EMOJI_SET_BASE_PATH.mkdir(parents=True, exist_ok=True)
    dummy_emoji_filename = "emoji_u1f600.png"
    dummy_texture_path = EMOJI_ASSET_BASE_PATH / DEFAULT_RESOLUTION_FOLDER / dummy_emoji_filename
    if not dummy_texture_path.exists():
        try:
            from PIL import Image
            img = Image.new('RGBA', (64, 64), (255, 128, 128, 255))
            img.save(dummy_texture_path)
        except ImportError: print(f"Pillow not installed. Cannot create dummy texture for {dummy_texture_path}.")
        except Exception as e: print(f"Error creating dummy texture: {e}")

    dummy_set_filepath = EMOJI_SET_BASE_PATH / DEFAULT_EMOJI_SET
    if not dummy_set_filepath.exists():
        try:
            with open(dummy_set_filepath, 'w') as f: json.dump({"Smileys & Emotion": ["😀", "😃", "😄"], "Info": "Dummy set"}, f)
        except Exception as e: print(f"Error creating dummy set file: {e}")

    app = EmojiApp()
    app.conceptual_shader_sourcing_info() # Print the research description
    
    Text(text="Keys: 1-4 Arrange | R IdleRot | T IdleZoom | N NodeAnim", position=(-0.85, 0.45), scale=0.7, background=True)
    Text(text="G Grayscale | S Sepia (S+Up/Down for amount) | B/A Conceptual Bloom/Afterimage", position=(-0.85, 0.40), scale=0.7, background=True)
    app.run()
```
