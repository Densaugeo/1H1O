import random, contextlib
from math import *

import bpy, mathutils # pyright: ignore - Pylance can't see mathutils

###########
# Helpers #
###########

def boolean(operation: str, mesh: bpy.types.Object | str,
    location: tuple[float, float, float],
    rotation: tuple[float, float, float] = None,
    scale   : tuple[float, float, float] = None, **mesh_args) -> None:
    '''
    Perform specified boolean operation of `mesh` with active Paragen context.
    If `mesh` is a string, bpy.ops.mesh.primitive_[mesh]_add() will be used to
    generate a temporary mesh. Additional arguments will either be passed to the
    mesh constructor (if `mesh` is a string)
    '''
    temporary_mesh = isinstance(mesh, str)
    if temporary_mesh: mesh = prim(mesh, **mesh_args)
    
    # Location is a required argument because if it isn't set, it'll default to
    # wherever Blender's 3D cursor is
    mesh.location = location
    if rotation is not None: mesh.rotation_euler = rotation
    if scale is not None: mesh.scale = scale
    
    # Sets bpy.context.active_object
    bpy.context.view_layer.objects.active = paragen_context.active[-1]
    
    booly = paragen_context.active[-1].modifiers.new(name='booly',
        type='BOOLEAN')
    booly.object = mesh
    booly.operation = operation
    bpy.ops.object.modifier_apply(modifier='booly')
    
    bpy.ops.object.select_all(action='DESELECT')
    if temporary_mesh:
        bpy.data.objects[mesh.name].select_set(True)
        bpy.ops.object.delete()

def union(*args, **kwargs):
    '''
    Alias for boolean('UNION', ...)
    '''
    return boolean('UNION', *args, **kwargs)

def difference(*args, **kwargs):
    '''
    Alias for boolean('DIFFERENCE', ...)
    '''
    return boolean('DIFFERENCE', *args, **kwargs)

def delete(*objects: bpy.types.Object) -> None:
    '''
    Deletes the supplied bpy objects
    '''
    bpy.ops.object.select_all(action='DESELECT')
    for object in objects:
        bpy.data.objects[object.name].select_set(True)
    bpy.ops.object.delete()

def material(name: str, base_color: tuple[float, float, float, float]) -> None:
    '''
    Create a GLTF-compatible material attached to the active Paragen context's
    base
    '''
    full_name = f'{paragen_context.active[-1].name}.{name}'
    
    if full_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[full_name])
    
    material = bpy.data.materials.new(full_name)
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'
        ].default_value = base_color
    paragen_context.active[-1].data.materials.append(material)

def prim(name: str, **mesh_args) -> bpy.types.Object:
    '''
    Create and return a bpy mesh. Uses bpy.ops.mesh.primitive_[name]_add() to
    build the mesh, and remaining arguments are passed through
    '''
    getattr(bpy.ops.mesh, f'primitive_{name}_add')(**mesh_args)
    return bpy.context.active_object

@contextlib.contextmanager
def paragen_context(bpy_object):
    paragen_context.active.append(bpy_object)
    
    if bpy.context.active_object is not None:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    
    matrix_world = bpy_object.matrix_world.copy()
    bpy_object.matrix_world = mathutils.Matrix()
    
    yield bpy_object
    
    bpy_object.matrix_world = matrix_world
    
    paragen_context.active.pop()
paragen_context.active = []

def paragen(func):
    def decorated_function(name, location=(0, 0, 0), rotation=(0, 0, 0),
        scale=(1, 1, 1), *args, **kwargs) -> None:
        # Can't run this in edit mode
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Make sure nothing is selected
        bpy.ops.object.select_all(action='DESELECT')
        
        # Remove old object. Old meshes remain in memory, but won't be saved
        if name in bpy.data.objects:
            bpy.data.objects[name].select_set(True)
            bpy.ops.object.delete()
        
        mesh = bpy.data.meshes.new(name)
        result = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(result)
        result.location = location
        result.rotation_euler = rotation
        result.scale = scale
        
        # Mesh sometimes changes name on its own so put it back
        result.data.name = name
        
        # Sets bpy.context.active_object. Sometimes this is already done
        # automatically, sometimes not
        bpy.context.view_layer.objects.active = result
        
        with paragen_context(result): func(*args, **kwargs)
        
        return result
    return decorated_function

##########
# Models #
##########

@paragen
def sad_scorpion_attempt():
    union('uv_sphere', radius=1, location=(0, 0, 0), scale=(1.5, 2, 1))
    
    for i in range(6):
        union('uv_sphere', radius=1,
            location=(-4*sin(pi*i/6), 0, 4 + 4*cos(pi*i/6)),
            scale=(1.5, 1.4 + 0.1*i, 1),
        )

@paragen
def sand_castle(tower_base_height=4, tower_peak_height=6):
    tower_cone_height = tower_peak_height - tower_base_height
    
    union('cylinder', radius=1.5, depth=2*tower_base_height,
        location=(0, 0, tower_base_height))
    
    union('cone', radius1=1.5, depth=1.5*tower_cone_height,
        location=(0, 0, 2*tower_base_height + 0.75*tower_cone_height))
    
    tower = prim('cylinder', radius=1, depth=tower_base_height)
    with paragen_context(tower):
        union('cone', radius1=1, depth=tower_cone_height,
            location=(0, 0, tower_peak_height/2))
    
    for x in [-10, 0, 10]:
        for y in [-10, 0, 10]:
            if x == y == 0: continue
            union(tower, location=(x, y, tower_base_height/2))
    
    wall = prim('cube')
    
    for θ in [0, 0.5*pi, pi, 1.5*pi]:
        # Outer wall
        union(wall,
            location=(10*cos(θ), 10*sin(θ), 0.4*tower_base_height),
            rotation=(0, 0, θ),
            scale=(0.3, 10, 0.4*tower_base_height),
        )
        
        # Inner wall
        union(wall,
            location=(5*cos(θ), 5*sin(θ), 0.3*tower_base_height),
            rotation=(0, 0, θ + pi/2),
            scale=(0.3, 5, 0.3*tower_base_height),
        )
    
    material('Sand', (0.65, 0.55, 0.15, 1.0))
    
    delete(tower, wall)

@paragen
def cactus_drink(height=2, spines=50, spine_seed=123, original=False):
    material('Cactus', (0.10, 0.60, 0.10, 1.0))
    
    union('cylinder', radius=1, depth=height, location=(0, 0, height/2))
    
    # Handle
    union('cylinder', radius=0.25, depth=height,
        location=(1.5, 0, height/2))
    bar = prim('cylinder', radius=0.1, depth=1, vertices=16)
    union(bar, location=(1, 0, height - 0.2), rotation=(0, pi/2, 0))
    union(bar, location=(1, 0,          0.2), rotation=(0, pi/2, 0))
    
    # Hollow part of cup
    if original: material('Water', (0.10, 0.10, 0.60, 1.0))
    difference('cylinder', radius=0.85,
        depth=0.4 if original else 2*(height - 0.15),
        location=(0, 0, height),
    )
    
    # Spines
    material('Spine', (0.80, 0.80, 0.10, 1.0))
    random.seed(spine_seed)
    spine = prim('cone', radius1=0.03, depth=0.5, vertices=8)
    for i in range(spines):
        θ = random.uniform(0.7, 2*pi - 0.7)
        z = random.uniform(0.1, height - 0.1)
        
        union(spine,
            location=(1.2*cos(θ), 1.2*sin(θ), z),
            rotation=(0, pi/2, θ)
        )
    
    delete(bar, spine)

def cactus_drink_2(name, height=2, **kwargs):
    cup = cactus_drink(f'{name}.Cup', height=height, **kwargs)
    water_location = cup.location.copy()
    water_location.z = height - 0.2
    water(f'{name}.Water', location=water_location, scale=(0.9, 0.9, 1))

@paragen
def water():
    material('Water', (0.10, 0.10, 0.60, 1.0))
    union('circle', radius=1, fill_type='TRIFAN', location=(0, 0, 0))

@paragen
def blocky_racer():
    material('Body', (0.5, 0.5, 0.5, 1.0))
    
    union('cube', location=(-3, 0, 1.750), scale=(1, 1.50, 0.750))
    union('cube', location=(-1, 0, 1.625), scale=(1, 1.25, 0.625))
    union('cube', location=( 1, 0, 1.500), scale=(1, 1.00, 0.500))
    union('cube', location=( 3, 0, 1.375), scale=(1, 0.75, 0.375))
    
    material('Wheel', (0.05, 0.05, 0.05, 1.0))
    for x in [-3, 3]:
        for y in [-3, 3]:
            union('cylinder', radius=1, depth=1, location=(x, y, 1), rotation=(pi/2, 0, 0))
    
    material('Shaft', (0.2, 0.2, 0.2, 1.0))
    for x in [-3, 3]:
        difference('cylinder', radius=0.3, depth=4.5, vertices=8, location=(x, 0, 1), rotation=(pi/2, 0, 0))
        union('cylinder', radius=0.15, depth=6, vertices=8, location=(x, 0, 1), rotation=(pi/2, 0, 0))

@paragen
def helicarrier(mid_segments=1):
    length = 80 + 40*mid_segments
    
    material('Blacktop', (0.02, 0.02, 0.02, 1.0))
    union('cube', location=(0, 0, -1), scale=(length/2, 10, 1))
    
    material('Gray Steel', (0.2, 0.2, 0.2, 1.0))
    
    angled_side_1 = prim('cube', scale=(10.5, 2, 1.2))
    for v in angled_side_1.data.vertices:
        if v.co.x > 0 and v.co.y > 0: v.co.y -= 3
    union(angled_side_1, location=( length/2 - 9.5,  12, -1), scale=( 1, 1, 1))
    union(angled_side_1, location=( length/2 - 9.5, -12, -1), scale=( 1, -1, 1))
    union(angled_side_1, location=(-length/2 + 9.5,  12, -1), scale=(-1, 1, 1))
    union(angled_side_1, location=(-length/2 + 9.5, -12, -1), scale=(-1, -1, 1))
    delete(angled_side_1)
    
    union('cube', location=( length/2 + 0.5, 0, -1), scale=(0.5, 10, 1.2))
    union('cube', location=(-length/2 - 0.5, 0, -1), scale=(0.5, 10, 1.2))
    
    rotor = prim('cube', scale=(10, 8, 1.2))
    for v in rotor.data.vertices: v.co.y -= 2
    
    with paragen_context(rotor):
        rotor_guard = prim('cube', scale=(10, 2, 1.2))
        for v in rotor_guard.data.vertices:
            if v.co.x > 0 and v.co.y > 0: v.co.x -= 4
            if v.co.x < 0 and v.co.y > 0: v.co.x += 4
        union(rotor_guard, location=(0, 8, 0))
        delete(rotor_guard)
        
        angled_side_2 = prim('cube', scale=(5, 4, 1.2))
        for v in angled_side_2.data.vertices:
            if v.co.x > 0 and v.co.y > 0: v.co.y -= 4
        union(angled_side_2, location=( 15, -6, 0), scale=( 1, 1, 1))
        union(angled_side_2, location=(-15, -6, 0), scale=(-1, 1, 1))
        delete(angled_side_2)
        
        difference('cylinder', location=(0, 0, 0), radius=7, depth=5)
    
    for i in range(mid_segments + 1):
        union(rotor, location=(length/2 - 40*(i + 1),  20, -1), scale=(1,  1, 1))
        union(rotor, location=(length/2 - 40*(i + 1), -20, -1), scale=(1, -1, 1))
    
    delete(rotor)

#########
# Scene #
#########

#sad_scorpion_attempt(name='Sad Scorpion Attempt', location=(0, 30, 0))
#sand_castle(name='Sand Castle', location=(0, 50, 0))
#cactus_drink(name='Cactus Drink', location=(0, 70, 0), original=True)
#cactus_drink_2(name='Cactus Drink 2', location=(-10, 70, 0))
blocky_racer(name='Racer', location=(0, 80, 0))
helicarrier(name='Helicarrier', location=(0, 100, 0), mid_segments=1)

# Unsolved problems:
# - How to select an individual vertex and move or merge it
# - How different material settings behave after export
# - How to manage trees of objects







