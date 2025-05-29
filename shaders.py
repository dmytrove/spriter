# This file will store GLSL shader code as Python strings

# --- Simple Effects ---

grayscale_shader_vert = """
#version 130
in vec2 position;
in vec2 uv;
out vec2 v_uv;

void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    v_uv = uv;
}
"""

grayscale_shader_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D tex; // Represents the screen texture

void main() {
    vec3 color = texture(tex, v_uv).rgb;
    float gray = dot(color, vec3(0.299, 0.587, 0.114));
    fragColor = vec4(vec3(gray), 1.0);
}
"""

sepia_shader_vert = grayscale_shader_vert # Vertex shader can often be reused

sepia_shader_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform float amount; // How much sepia to apply (0.0 to 1.0)

void main() {
    vec3 color = texture(tex, v_uv).rgb;
    vec3 sepia_color = vec3(
        dot(color, vec3(0.393, 0.769, 0.189)),
        dot(color, vec3(0.349, 0.686, 0.168)),
        dot(color, vec3(0.272, 0.534, 0.131))
    );
    fragColor = vec4(mix(color, sepia_color, amount), 1.0);
}
"""

# --- Conceptual Bloom Shaders ---

bloom_brightness_extract_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform float threshold; // e.g., 0.7

void main() {
    vec4 color = texture(tex, v_uv);
    float brightness = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
    if (brightness > threshold) {
        fragColor = color;
    } else {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
}
"""

# Simple Box Blur (for conceptual demonstration, Gaussian is better but more complex)
# This would typically be applied in two passes (horizontal then vertical)
blur_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D tex;
uniform vec2 texel_size; // 1.0 / texture_width, 1.0 / texture_height
uniform vec2 blur_direction; // e.g., (1.0, 0.0) for horizontal, (0.0, 1.0) for vertical
uniform float blur_radius_pixels; // How many pixels to blur

void main() {
    vec4 sum = vec4(0.0);
    float count = 0.0;
    // Simple box blur
    for (float i = -blur_radius_pixels; i <= blur_radius_pixels; i += 1.0) {
        sum += texture(tex, v_uv + i * texel_size * blur_direction);
        count += 1.0;
    }
    fragColor = sum / count;
}
"""

bloom_composite_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D original_tex;
uniform sampler2D blurred_bloom_tex;
uniform float bloom_intensity;

void main() {
    vec4 original_color = texture(original_tex, v_uv);
    vec4 bloom_color = texture(blurred_bloom_tex, v_uv);
    fragColor = original_color + bloom_color * bloom_intensity;
    // Could also use screen blend: 1.0 - (1.0 - original_color) * (1.0 - bloom_color)
}
"""

# --- Conceptual Afterimage Shader ---

afterimage_frag = """
#version 130
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D current_frame_tex;
uniform sampler2D previous_frame_tex; // Texture of the last composed frame
uniform float damp; // e.g., 0.85 to 0.95

void main() {
    vec4 current_color = texture(current_frame_tex, v_uv);
    vec4 previous_color = texture(previous_frame_tex, v_uv);
    fragColor = mix(current_color, previous_color, damp);
}
"""
```
