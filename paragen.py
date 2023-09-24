import random, contextlib, dataclasses, typing
from math import *

import bpy, mathutils # pyright: ignore - Pylance can't see mathutils

###########
# Helpers #
###########

# Maybe I should trying renaming 'mesh' to 'bpy_object', since it's not really
# a mesh
def boolean(operation: str, mesh: bpy.types.Object | str,
    p: tuple[float, float, float] = (0, 0, 0),
    px: float = None,
    py: float = None,
    pz: float = None,
    r: tuple[float, float, float] = (0, 0, 0),
    rx: float = None,
    ry: float = None,
    rz: float = None,
    s: tuple[float, float, float] = (1, 1, 1),
    sx: float = None,
    sy: float = None,
    sz: float = None, **mesh_args) -> None:
    '''
    Perform specified boolean operation of `mesh` with active Paragen context.
    If `mesh` is a string, bpy.ops.mesh.primitive_[mesh]_add() will be used to
    generate a temporary mesh. Additional arguments will be passed to the mesh
    constructor (if `mesh` is a string)
    '''
    if isinstance(mesh, str): mesh = prim(mesh, **mesh_args)
    
    # Location is a required argument because if it isn't set, it'll default to
    # wherever Blender's 3D cursor is
    mesh.location = p
    if px is not None: mesh.location[0] = px
    if py is not None: mesh.location[1] = py
    if pz is not None: mesh.location[2] = pz
    mesh.rotation_euler = r
    if rx is not None: mesh.rotation_euler[0] = rx
    if ry is not None: mesh.rotation_euler[1] = ry
    if rz is not None: mesh.rotation_euler[2] = rz
    mesh.scale = s
    if sx is not None: mesh.scale[0] = sx
    if sy is not None: mesh.scale[1] = sy
    if sz is not None: mesh.scale[2] = sz
    
    # Sets bpy.context.active_object
    bpy.context.view_layer.objects.active = paragen_stack[-1].bpy_object
    
    booly = paragen_stack[-1].bpy_object.modifiers.new(name='booly',
        type='BOOLEAN')
    booly.object = mesh
    booly.operation = operation
    bpy.ops.object.modifier_apply(modifier='booly')
    
    bpy.ops.object.select_all(action='DESELECT')

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

def material(name: str, base_color: tuple[float, float, float, float],
    metallic: float = 0.0) -> bpy.types.Material:
    '''
    Create a GLTF-compatible material attached to the active Paragen context's
    base
    '''
    assert 0 <= metallic <= 1
    
    full_name = get_name_prefix() + name
    
    if full_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[full_name])
    
    material = bpy.data.materials.new(full_name)
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'
        ].default_value = base_color
    material.node_tree.nodes['Principled BSDF'].inputs['Metallic'
        ].default_value = metallic
    paragen_stack[-1].bpy_object.data.materials.append(material)
    
    return material

def blank(name: str, materials: [bpy.types.Material] = []) -> bpy.types.Object:
    '''
    Create and return a blank bpy object
    '''
    full_name = get_name_prefix() + name
    
    mesh = bpy.data.meshes.new(full_name)
    bpy_object = bpy.data.objects.new(full_name, mesh)
    bpy.context.scene.collection.objects.link(bpy_object)
    paragen_stack[-1].temps.append(bpy_object)
    
    for material in materials:
        mesh.materials.append(material)
    
    return bpy_object

def prim(name: str, material: bpy.types.Material = None,
    p: tuple[float, float, float] = (0, 0, 0),
    px: float = None,
    py: float = None,
    pz: float = None,
    r: tuple[float, float, float] = (0, 0, 0),
    rx: float = None,
    ry: float = None,
    rz: float = None,
    s: tuple[float, float, float] = (1, 1, 1),
    sx: float = None,
    sy: float = None,
    sz: float = None, **mesh_args) -> bpy.types.Object:
    '''
    Create and return a bpy mesh. Uses bpy.ops.mesh.primitive_[name]_add() to
    build the mesh, optionally applies a material if passed in, and remaining
    arguments are passed through
    '''
    mesh_args['location'] = p
    mesh_args['rotation'] = r
    mesh_args['scale'] = s
    
    getattr(bpy.ops.mesh, f'primitive_{name}_add')(**mesh_args)
    result = bpy.context.active_object
    
    if px is not None: result.location[0] = px
    if py is not None: result.location[1] = py
    if pz is not None: result.location[2] = pz
    if rx is not None: result.rotation_euler[0] = rx
    if ry is not None: result.rotation_euler[1] = ry
    if rz is not None: result.rotation_euler[2] = rz
    if sx is not None: result.scale[0] = sx
    if sy is not None: result.scale[1] = sy
    if sz is not None: result.scale[2] = sz
    
    if material is not None:
        result.data.materials.append(material)
    
    paragen_stack[-1].temps.append(result)
    
    return result

def instance(name: str, bpy_object: bpy.types.Object | str,
    p: tuple[float, float, float] = (0, 0, 0),
    px: float = None,
    py: float = None,
    pz: float = None,
    r: tuple[float, float, float] = (0, 0, 0),
    rx: float = None,
    ry: float = None,
    rz: float = None,
    s: tuple[float, float, float] = (1, 1, 1),
    sx: float = None,
    sy: float = None,
    sz: float = None, **bpy_args) -> None:
    '''
    Creates a new instance of a given bpy objext. Automatically adds it to
    current scene and paragen object. If `bpy_object` is a string,
    bpy.ops.mesh.primitive_[bpy_object]_add() will be used to generate a
    temporary bpy_object. Additional arguments will be passed to the bpy_object
    constructor (if `bpy_object` is a string)
    '''
    if isinstance(bpy_object, str): bpy_object = prim(bpy_object, **bpy_args)
    
    result = bpy_object.copy()
    result.parent = paragen_stack[-1].bpy_object
    bpy.context.scene.collection.objects.link(result)
    
    result.name = get_name_prefix() + name
    result.location = p
    if px is not None: result.location[0] = px
    if py is not None: result.location[1] = py
    if pz is not None: result.location[2] = pz
    result.rotation_euler = r
    if rx is not None: result.rotation_euler[0] = rx
    if ry is not None: result.rotation_euler[1] = ry
    if rz is not None: result.rotation_euler[2] = rz
    result.scale = s
    if sx is not None: result.scale[0] = sx
    if sy is not None: result.scale[1] = sy
    if sz is not None: result.scale[2] = sz

@dataclasses.dataclass
class ParagenStackLayer:
    bpy_object: bpy.types.Object
    temps: typing.List[bpy.types.Object] = \
        dataclasses.field(default_factory=list)
paragen_stack: typing.List[ParagenStackLayer] = []

def get_name_prefix() -> str:
    return paragen_stack[-1].bpy_object.name + '.'

@contextlib.contextmanager
def paragen_context(bpy_object):
    paragen_stack.append(ParagenStackLayer(bpy_object))
    
    if bpy.context.active_object is not None:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    
    matrix_world = bpy_object.matrix_world.copy()
    bpy_object.matrix_world = mathutils.Matrix()
    
    yield bpy_object
    
    bpy.ops.object.select_all(action='DESELECT')
    for object in paragen_stack[-1].temps:
        bpy.data.objects[object.name].select_set(True)
    bpy.ops.object.delete()
    
    bpy_object.matrix_world = matrix_world
    
    paragen_stack.pop()

def paragen(func):
    def decorated_function(name,
        p: tuple[float, float, float] = (0, 0, 0),
        px: float = None,
        py: float = None,
        pz: float = None,
        r: tuple[float, float, float] = (0, 0, 0),
        rx: float = None,
        ry: float = None,
        rz: float = None,
        s: tuple[float, float, float] = (1, 1, 1),
        sx: float = None,
        sy: float = None,
        sz: float = None,
        *args, **kwargs) -> None:
        # Can't run this in edit mode
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Make sure nothing is selected
        bpy.ops.object.select_all(action='DESELECT')
        
        # Remove old object and children. Old meshes remain in memory, but won't
        # be saved
        if name in bpy.data.objects:
            bpy.data.objects[name].select_set(True)
            for object in bpy.data.objects[name].children:
                object.select_set(True)
            bpy.ops.object.delete()
        
        mesh = bpy.data.meshes.new(name)
        result = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(result)
        result.location = p
        if px is not None: result.location[0] = px
        if py is not None: result.location[1] = py
        if pz is not None: result.location[2] = pz
        result.rotation_euler = r
        if rx is not None: result.rotation_euler[0] = rx
        if ry is not None: result.rotation_euler[1] = ry
        if rz is not None: result.rotation_euler[2] = rz
        result.scale = s
        if sx is not None: result.scale[0] = sx
        if sy is not None: result.scale[1] = sy
        if sz is not None: result.scale[2] = sz
        
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
    union('uv_sphere', radius=1, s=(1.5, 2, 1))
    
    for i in range(6):
        union('uv_sphere', radius=1,
            p=(-4*sin(pi*i/6), 0, 4 + 4*cos(pi*i/6)),
            s=(1.5, 1.4 + 0.1*i, 1),
        )

@paragen
def sand_castle(tower_base_height=4, tower_peak_height=6):
    tower_cone_height = tower_peak_height - tower_base_height
    
    union('cylinder', radius=1.5, depth=2*tower_base_height,
        p=(0, 0, tower_base_height))
    
    union('cone', radius1=1.5, depth=1.5*tower_cone_height,
        p=(0, 0, 2*tower_base_height + 0.75*tower_cone_height))
    
    tower = prim('cylinder', radius=1, depth=tower_base_height)
    with paragen_context(tower):
        union('cone', radius1=1, depth=tower_cone_height,
            p=(0, 0, tower_peak_height/2))
    
    for x in [-10, 0, 10]:
        for y in [-10, 0, 10]:
            if x == y == 0: continue
            union(tower, p=(x, y, tower_base_height/2))
    
    wall = prim('cube')
    
    for θ in [0, 0.5*pi, pi, 1.5*pi]:
        # Outer wall
        union(wall,
            p=(10*cos(θ), 10*sin(θ), 0.4*tower_base_height),
            rz=θ,
            s=(0.3, 10, 0.4*tower_base_height),
        )
        
        # Inner wall
        union(wall,
            p=(5*cos(θ), 5*sin(θ), 0.3*tower_base_height),
            rz=θ + pi/2,
            s=(0.3, 5, 0.3*tower_base_height),
        )
    
    material('Sand', (0.65, 0.55, 0.15, 1.0))

@paragen
def cactus_drink(height=2, spines=50, spine_seed=123, original=False):
    material('Cactus', (0.10, 0.60, 0.10, 1.0))
    
    union('cylinder', radius=1, depth=height, p=(0, 0, height/2))
    
    # Handle
    union('cylinder', radius=0.25, depth=height,
        p=(1.5, 0, height/2))
    bar = prim('cylinder', radius=0.1, depth=1, vertices=16)
    union(bar, p=(1, 0, height - 0.2), ry=pi/2)
    union(bar, p=(1, 0,          0.2), ry=pi/2)
    
    # Hollow part of cup
    if original: material('Water', (0.10, 0.10, 0.60, 1.0))
    difference('cylinder', radius=0.85,
        depth=0.4 if original else 2*(height - 0.15),
        pz=height,
    )
    
    # Spines
    material('Spine', (0.80, 0.80, 0.10, 1.0))
    random.seed(spine_seed)
    spine = prim('cone', radius1=0.03, depth=0.5, vertices=8)
    for i in range(spines):
        θ = random.uniform(0.7, 2*pi - 0.7)
        z = random.uniform(0.1, height - 0.1)
        
        union(spine,
            p=(1.2*cos(θ), 1.2*sin(θ), z),
            ry=pi/2,
        )

def cactus_drink_2(name, height=2, **kwargs):
    cup = cactus_drink(f'{name}.Cup', height=height, **kwargs)
    water_location = cup.location.copy()
    water_location.z = height - 0.2
    water(f'{name}.Water', p=water_location, s=(0.9, 0.9, 1))

@paragen
def water():
    material('Water', (0.10, 0.10, 0.60, 1.0))
    union('circle', radius=1, fill_type='TRIFAN', p=(0, 0, 0))

@paragen
def blocky_racer():
    material('Body', (0.5, 0.5, 0.5, 1.0))
    
    union('cube', p=(-3, 0, 1.750), s=(1, 1.50, 0.750))
    union('cube', p=(-1, 0, 1.625), s=(1, 1.25, 0.625))
    union('cube', p=( 1, 0, 1.500), s=(1, 1.00, 0.500))
    union('cube', p=( 3, 0, 1.375), s=(1, 0.75, 0.375))
    
    material('Wheel', (0.05, 0.05, 0.05, 1.0))
    for x in [-3, 3]:
        for y in [-3, 3]:
            union('cylinder', radius=1, depth=1, p=(x, y, 1), rx=pi/2)
    
    material('Shaft', (0.2, 0.2, 0.2, 1.0))
    for x in [-3, 3]:
        difference('cylinder', radius=0.3, depth=4.5, vertices=8, p=(x, 0, 1), rx=pi/2)
        union('cylinder', radius=0.15, depth=6, vertices=8, p=(x, 0, 1), rx=pi/2)

@paragen
def helicarrier(mid_segments=1):
    length = 80 + 40*mid_segments
    
    material('Blacktop', (0.02, 0.02, 0.02, 1.0))
    union('cube', p=(0, 0, -1), s=(length/2, 10, 1))
    
    material('Gray Steel', (0.2, 0.2, 0.2, 1.0))
    
    angled_side_1 = prim('cube', s=(10.5, 2, 1.2))
    for v in angled_side_1.data.vertices:
        if v.co.x > 0 and v.co.y > 0: v.co.y -= 3
    union(angled_side_1, p=( length/2 - 9.5,  12, -1), s=( 1, 1, 1))
    union(angled_side_1, p=( length/2 - 9.5, -12, -1), s=( 1, -1, 1))
    union(angled_side_1, p=(-length/2 + 9.5,  12, -1), s=(-1, 1, 1))
    union(angled_side_1, p=(-length/2 + 9.5, -12, -1), s=(-1, -1, 1))
    
    union('cube', p=( length/2 + 0.5, 0, -1), s=(0.5, 10, 1.2))
    union('cube', p=(-length/2 - 0.5, 0, -1), s=(0.5, 10, 1.2))
    
    rotor = prim('cube', s=(10, 8, 1.2))
    for v in rotor.data.vertices: v.co.y -= 2
    
    with paragen_context(rotor):
        rotor_guard = prim('cube', s=(10, 2, 1.2))
        for v in rotor_guard.data.vertices:
            if v.co.x > 0 and v.co.y > 0: v.co.x -= 4
            if v.co.x < 0 and v.co.y > 0: v.co.x += 4
        union(rotor_guard, p=(0, 8, 0))
        
        angled_side_2 = prim('cube', s=(5, 4, 1.2))
        for v in angled_side_2.data.vertices:
            if v.co.x > 0 and v.co.y > 0: v.co.y -= 4
        union(angled_side_2, p=( 15, -6, 0))
        union(angled_side_2, p=(-15, -6, 0), sx=-1)
        
        difference('cylinder', p=(0, 0, 0), radius=7, depth=5)
    
    for i in range(mid_segments + 1):
        union(rotor, p=(length/2 - 40*(i + 1),  20, -1))
        union(rotor, p=(length/2 - 40*(i + 1), -20, -1), sy=-1)

@paragen
def head():
    material('Base', (0.2, 0.2, 0.2, 1.0))
    union('cube', s=(1, 0.1, 0.1))

@paragen
def gramorgan():
    material('Base', (0.2, 0.2, 0.2, 1.0))
    union('cube', pz=0.25, s=(7, 2, 0.25))
    
    l = 8
    r = 0.25
    x = -6.5
    y = 1.5
    for i in range(8):
        union('cylinder', p=(x, y, l/2 + 0.5), radius=r + 0.05, depth=l, vertices=16)
        difference('cylinder', p=(x, y, l/2 + 0.5), radius=r, depth=l, vertices=16)
        x += 2*r + 0.15
        l *= 0.90
        r *= 0.95
    
    l = 7
    r = 0.25
    x = 6.5
    y = 1.5
    for i in range(8):
        union('cylinder', p=(x, y, l/2 + 0.5), radius=r + 0.05, depth=l, vertices=16)
        difference('cylinder', p=(x, y, l/2 + 0.5), radius=r, depth=l, vertices=16)
        x -= 2*r + 0.15
        l *= 0.90
        r *= 0.95
    
    nest_test = head('gramo whatsit head')
    union(nest_test, p=(0, 0, 1), rz=pi/4)
    
    material('Disc', (0.02, 0.02, 0.02, 1.0))
    # 12 in record
    union('cylinder', p=(0, 0, 0.5), radius=3.048/2, depth=0.1)

@paragen
def circus_tent(radius=10, height=8):
    material('Red Canvas', base_color=(0.9, 0.02, 0.02, 1.0))
    
    union('cone', pz=height - 6/2, radius1=radius, depth=6)
    union('cylinder', pz=height - 6.5, radius=radius, depth=1)
    
    cut = prim('cylinder', radius=radius - 0.1, depth=1)
    with paragen_context(cut):
        union('cone', pz=3.5 - 0.05, radius1=radius - 0.1, depth=5.9)
    difference(cut, pz=height - 6.5)
    
    material('Wood', base_color=(0.287, 0.111, 0.016, 1))
    union('cylinder', pz=height/2 - 0.1, radius=0.2, depth=height - 0.2, vertices=16)
    
    union('cylinder', p=(radius - 0.2, 0, (height - 6)/2), radius=0.15, depth=height - 6, vertices=16)

@paragen
def gazebo(height=7.5, radius=8, pillars=5):
    material('Stone', base_color=(0.3, 0.3, 0.3, 1))
    
    # Base (light sections)
    union('cylinder', pz=0.375, radius=radius - 0.5, depth=0.25)
    union('cylinder', pz=0.875, radius=radius - 1.5, depth=0.25)
    
    # Ring above pillars
    union('cylinder',
        pz=height - 2.25,
        radius=radius - 1,
        depth=0.5,
    )
    difference('cylinder',
        pz=height - 2.25,
        radius=radius - 3,
        depth=0.5,
    )
    
    # Roof
    union('cylinder',
        pz=height - 0.25,
        radius=radius - 2.5,
        depth=0.5,
    )
    
    material('Dark Stone', base_color=(0.1, 0.1, 0.1, 1))
    
    # Base (dark sections)
    union('cylinder', pz=0.125, radius=radius - 0.0, depth=0.25)
    union('cylinder', pz=0.625, radius=radius - 1.0, depth=0.25)
    
    # Central pillar
    union('cylinder',
        pz=1 + (height - 1.5)/2,
        radius = 0.75,
        depth=height - 1.5,
    )
    
    # Ring of pillars
    for i in range(pillars):
        θ = i/pillars*2*pi
        x = (radius - 1.5)*cos(θ)
        y = (radius - 1.5)*sin(θ)
        
        union('cylinder',
            p=(x, y, (height - 1.75)/2),
            radius=(0.5),
            depth=height - 3.25,
            vertices=16,
        )

@paragen
def door():
    material('Black Stone', base_color=(0.05, 0.05, 0.05, 1))
    
    union('cube', p=(2.25, 0, 3.5), s=(2.5, 0.25, 3.5))
    
    material('Dark Stone', base_color=(0.2, 0.2, 0.2, 1))
    
    for z in [1, 3.5, 6]:
        union('cube', p=(2.25, 0, z), s=(2.5, 0.5, 0.5))

@paragen
def gate():
    material('Stone', base_color=(0.3, 0.3, 0.3, 1))
    
    union('cube', p=(0, 0, -0.25), s=(8, 8, 0.25))
    
    union('cube', p=(0, 0, 4), s=(6, 1, 4))
    difference('cube', p=(0, 0, 3.5), s=(5, 1, 3.5))
    
    left_door = door(name='Left Door', p=(-4.75, 0, 0))
    left_door.parent = paragen_stack[-1].bpy_object
    
    right_door = door(name='Right Door', p=(4.75, 0, 0), rz=pi)
    right_door.parent = paragen_stack[-1].bpy_object
    
    for sign in [-1, 1]:
        union('cube', p=(sign*5.5, -3.5, 1.5), s=(0.5, 0.5, 1.5))
        union('cube', p=(sign*5.5,  3.5, 1.5), s=(0.5, 0.5, 1.5))
    
    material('Black Stone', base_color=(0.05, 0.05, 0.05, 1))
    
    for sign in [-1, 1]:
        union('cube', p=(sign*7, 0, 3), s=(1, 0.25, 3))
        union('cube', p=(sign*5.5, 0, 1), s=(0.25, 3, 1))

@paragen
def pin_wheel_windmill_spinner(blades=3, blade_length=25):
    material('Steel', base_color=(0.7, 0.7, 0.7, 1))
    
    union('cone', pz=0.25, radius1=0.5, radius2=0.35, depth=0.5, vertices=8)
    union('cone', pz=0.75, radius1=0.35, radius2=0, depth=0.5, vertices=8)
    
    for i in range(blades):
        θ = 2*pi*i/blades
        
        material(f'Blade {i}', base_color=(
            1 if (i + 0) % 6 < 3 else 0,
            1 if (i + 2) % 6 < 3 else 0,
            1 if (i + 4) % 6 < 3 else 0,
            1,
        ))
        
        union('cube',
            p=(cos(θ)*blade_length/2, sin(θ)*blade_length/2, 0.1), 
            rz=θ,
            s=(blade_length/2, 0.25, 0.05),
        )

@paragen
def pinwheel_windmill(height=100, blades=3, blade_length=25):
    material('Steel', base_color=(0.7, 0.7, 0.7, 1))
    
    union('cone', p=(0, 0, height/2), depth=height, radius1=1, radius2=0.5)
    union('cube', p=(0, 0.5, height + 0.6), s=(0.6, 1.1, 0.6))
    union('cylinder', p=(0, 0, height + 0.6), rx=pi/2, radius=0.4, vertices=8)
    
    spinner = pin_wheel_windmill_spinner(
        name=get_name_prefix() + 'Spinner',
        p=(0, -0.7, height + 0.6),
        rx=pi/2,
        blades=blades,
        blade_length=blade_length,
    )
    spinner.parent = paragen_stack[-1].bpy_object

@paragen
def lego_couch(width=12, depth=4):
    material('Green', base_color=(0.1, 0.5, 0.1, 1))
    
    # Cushions
    union('cube', p=(0, 0, 2.4), s=(width/2, depth/2, 0.8))
    
    # Back
    union('cube', p=(0, depth/2 - 0.5, 4), s=(width/2 - 1, 0.5, 1.2))
    for i in range(width - 2):
        union('cylinder', p=(i - width/2 + 1.5, depth/2 - 0.5, 5.3), radius=0.3, depth=0.2, vertices=8)
    
    # Arms
    for x in [-width/2 + 0.5, width/2 - 0.5]:
        union('cube', p=(x, 0, 3.6), s=(0.5, depth/2, 0.4))
        for i in range(depth):
            union('cylinder', p=(x, i - depth/2 + 0.5, 4.1), radius=0.3, depth=0.2, vertices=8)
    
    material('Black', base_color=(0.1, 0.1, 0.1, 1))
    
    # Base
    union('cube', p=(0, 0, 1.4), s=(width/2, depth/2, 0.2))
    
    # Legs
    for x in [-width/2 + 0.5, width/2 - 0.5]:
        for y in [-depth/2 + 0.5, depth/2 - 0.5]:
            union('cylinder', p=(x, y, 0.6), depth=1.2, radius=0.5, vertices=8)

@paragen
def tunnel(width=8, height=4, segments=8):
    stone = material('Stone', base_color=(0.2, 0.2, 0.2, 1))
    dark_stone = material('Dark Stone', base_color=(0.1, 0.1, 0.1, 1))
    
    # Floor + ceiling
    for z in [0.5, height + 1.5]:
        union('cube', material=stone,
            p=(0, 4*segments + 0.5, z),
            s=(width/2, 4*segments + 0.5, 0.5),
        )
    
    # Wall
    for x_sign in [-1, 1]:
        union('cube', material=stone,
            p=(x_sign*(width/2 + 0.5), 4*segments + 0.5, height/2 + 1),
            s=(0.5, 4*segments + 0.5, height/2 + 1),
        )
    
    brace = blank('BraceTemplate', materials=[dark_stone])
    brace.data.materials.append(dark_stone)
    with paragen_context(brace):
        # Wall pillar
        for x_sign in [-1, 1]:
            union('cube',
                p=(x_sign*(width/2 - 0.5), 0, height/2),
                s=(0.5, 0.5, height/2),
            )
        
        # Roof beam
        union('cube',
            p=(0, 0, height - 0.5),
            s=(width/2 - 1, 0.5, 0.5),
        )
    
    arch = blank('ArchTemplate', materials=[stone, dark_stone])
    with paragen_context(arch):
        # Wall arch
        for p in [
            (-width/2 + 0.5, 1, height - 2.5),
            (-width/2 + 0.5, 2, height - 1.5),
            (-width/2 + 0.5, 3, height - 0.5),
        ]:
            union('cube', material=dark_stone,
                p=p,
                s=(0.5, 0.5, 0.5),
            )
        
        # Infill above wall arch
        union('cube', material=stone,
            p=(-width/2 + 0.5, 1, height - 1),
            s=(0.5, 0.5, 1),
        )
        union('cube', material=stone,
            p=(-width/2 + 0.5, 2, height - 0.5),
            s=(0.5, 0.5, 0.5),
        )
    
    for i in range(segments + 1):
        p = (0, 8*i + 0.5, 1)
        
        instance(f'Brace{i}', brace, p=p)
        
        if i != segments:
            instance(f'Arch{i}-0', arch, p=p, scale=( 1,  1, 1))
            instance(f'Arch{i}-1', arch, p=p, s=(-1,  1, 1))
        
        if i != 0:
            instance(f'Arch{i}-2', arch, p=p, s=( 1, -1, 1))
            instance(f'Arch{i}-3', arch, p=p, s=(-1, -1, 1))

# This pear leaves a lot of internal objects when it's done that aren't
# necessary. Needs some way of merging them into a single geometry. Considering
# the number of different Blender functions needed for this, probably not worth
# sorting out until after switching to webassembly
@paragen
def lego_pear(radius=4, bumps=True):
    # Standard RGB values are 0x009247 for green and 0x9aca3a for light green.
    # Conversion so Blender RGB is not strightforward - the numbers used here
    # were obtained by entering the above hex values into Blender's GUI and
    # copying the RGB back out (and 0x692e14 for brown)
    green = material('Green', base_color=(0, 0.287441, 0.06301, 1))
    light_green = material('Light Green', base_color=(0.323143, 0.590619, 0.042312, 1))
    brown = material('Brown', base_color=(0.141263, 0.027321, 0.006995, 1))
    
    light_green_block = prim('cube', s=(0.5, 0.5, 0.6), material=light_green)
    
    green_bump = prim('cylinder', radius=0.3, depth=0.2, vertices=8,
        material=green)
    light_green_bump = prim('cylinder', radius=0.3, depth=0.2, vertices=8,
        material=light_green)
    
    layers = []
    
    for i in range(1, radius):
        layers.append(radius - radius/(2**i))
        if radius/(2**i) <= 1: break
    
    # Central piece
    for _ in range(radius): layers.append(radius)
    
    # Cone-shaped top part of fruit body
    for i in range(radius - 1, 1, -1):
        layers.append(i + 0.75)
        layers.append(i)
    
    # Top layer is just a 2x2 square (so radius=1, no 1.75 intermediary)
    layers.append(1)
    
    # Make all those layers
    for i, r in enumerate(layers):
        for x in range(-ceil(r), ceil(r)):
            for y in range(-ceil(r), ceil(r)):
                if (x + 0.5)**2 + (y + 0.5)**2 < r**2:
                    instance('Pear Block-{x}-{y}', light_green_block, p=(x + 0.5, y + 0.5, 0.6 + 1.2*i))
                    
                    if bumps:
                        instance('Pear Block Bump-{x}-{y}', light_green_bump, p=(x + 0.5, y + 0.5, 1.3 + 1.2*i))
    
    # Stem
    union('cube', p=(0, -0.5, 0.6 + 1.2*len(layers)), s=(1, 0.5, 0.6), material=brown)
    
    # Leaf
    union('cube', p=(0, 0, 1.8 + 1.2*len(layers)), s=(1, 2, 0.6), material=green)
    if bumps:
        for x in [-0.5, 0.5]:
            for y in [-1.5, -0.5, 0.5, 1.5]:
                instance(f'Bump-{x}-{y}', green_bump, p=(x, y, 2.5 + 1.2*len(layers)))

@paragen
def pencil_tower(levels=6, angle=0.245, lead_height=7):
    # 20 for the eraser + sleeve at the base, 5*sin(angle) for the tip
    height = levels*10 + 20 + 5/sin(angle)
    
    wall_surface = material('Wall Surface', base_color=(0.0, 0.2, 0.8, 1))
    
    union('cylinder', vertices=6,
        pz=height/2 + 10,
        s=(5, 5, height/2 - 10),
        material=wall_surface,
    )
    boolean('INTERSECT', 'cone', depth=height, radius1=tan(angle)*height,
        radius2=0, vertices=36,
        pz=height/2,
        material=material('Exposed Wood', base_color=(0.5, 0.5, 0.3, 1)),
    )
    difference('cube',
        pz=height,
        s=(10, 10, lead_height),
    )
    union('cone', depth=lead_height, radius1=tan(angle)*lead_height,
        radius2=0, vertices=36,
        pz=height - lead_height/2,
        material=material('Lead', base_color=(0.1, 0.1, 0.1, 1)),
    )
    
    instance('Eraser', 'cylinder', depth=10, radius=5, vertices=36,
        pz=5,
        material=material('Rubber', base_color=(0.55, 0.06, 0.21, 1)),
    )
    
    instance('Sleeve', 'cylinder', depth=12, radius=5.5, vertices=36,
        pz=15,
        material=material('Brass', base_color=(0.8, 0.8, 0.2, 1)),
    )
    
    glass = material('Glass', base_color=(0.1, 0.8, 0.8, 1))
    
    window = prim('cube', s=(0.25, 1.5, 2.5), material=glass)
    for level in range(levels):
        for i in range(6):
            θ = i*pi/3
            apothem = 5*sqrt(3)/2
            x = apothem*cos(θ)
            y = apothem*sin(θ)
            instance(f'Window{level}-{i}', window,
                p=(x, y, 25 + 10*level),
                rz=θ,
            )
    
    doorway = blank('Doorway', materials=[wall_surface])
    with paragen_context(doorway):
        union('cube', p=(0, 0, 3), s=(2.5, 2, 3))
        difference('cube', p=(0, 0, 2.75), s=(2, 3, 2.75))
    instance('Doorway', doorway, p=(0, -5, 0))
    
    instance('Door', 'cube',
        p=(0, -6, 2.75),
        s=(2, 0.1, 2.75),
        material=glass,
    )

@paragen
def geometry_crusher():
    blue_steel = material('Blue Steel', base_color=(0.25, 0.25, 0.75, 1),
        metallic=1)
    gray_steel = material('Gray Steel', base_color=(0.75, 0.75, 0.75, 1),
        metallic=1)
    
    union('cube', p=(0, 0, 6), s=(4, 4, 2), material=blue_steel)
    difference('cube', p=(0, 0, 8), s=(2, 2, 1), material=blue_steel)
    difference('cube', p=(0, 0, 4), s=(2, 1, 1), material=blue_steel)
    difference('cube', p=(0, 0, 6), s=(3.9, 3.9, 1.9), material=blue_steel)
    
    union('cone', radius1=2.1*sqrt(2), radius2=3.1*sqrt(2), depth=2,
        vertices=4,
        p=(0, 0, 9), rz=pi/4, material=gray_steel)
    difference('cone', radius1=2*sqrt(2), radius2=3*sqrt(2), depth=2,
        vertices=4,
        p=(0, 0, 9), rz=pi/4, material=gray_steel)
    
    leg = prim('cube', s=(0.35, 0.35, 4.05), material=gray_steel)
    for x in [-3.75, 3.75]:
        for y in [-3.75, 3.75]:
            instance('Leg', leg, p=(x, y, 4.05))

@paragen
def conveyor(width=2, length=8, height=4):
    blue_steel = material('Blue Steel', base_color=(0.25, 0.25, 0.75, 1),
        metallic=1)
    gray_steel = material('Gray Steel', base_color=(0.75, 0.75, 0.75, 1),
        metallic=1)
    neoprene = material('Neoprene', base_color=(0.05, 0.05, 0.05, 1))
    
    leg = prim('cube', s=(0.25, 0.25, height/2 + 0.05), material=gray_steel)
    for x in [-length/2, length/2]:
        for y in [-width/2 - 0.5, width/2 + 0.5]:
            instance('Leg', leg, p=(x, y, height/2 + 0.05))
    
    rail = prim('cube', s=(length/2, 0.1, 0.25), material=blue_steel)
    for y in [-width/2 - 0.5, width/2 + 0.5]:
        instance('Rail', rail, p=(0, y, height - 0.25))
    
    roller = prim('cylinder', radius=0.15, depth=width + 1, vertices=16, material=gray_steel)
    roller_count = floor(length/0.5) + 1
    roller_spacing = length/(roller_count - 1)
    for i in range(roller_count):
        instance('Roller', roller,
            p=(-length/2 + roller_spacing*i, 0, height - 0.25), rx=pi/2)
    
    for x in [-length/2, length/2]:
        union('cylinder', radius=0.25, depth=width, vertices=16,
            p=(x, 0, height - 0.25), rx=pi/2, material=neoprene)
        difference('cylinder', radius=0.15, depth=width, vertices=16,
            p=(x, 0, height - 0.25), rx=pi/2, material=neoprene)
    for x in [-length/2 + 0.15, length/2 - 0.15]:
        difference('cube', p=(x, 0, height - 0.25), s=(0.15, width + 1, 1),
            material=neoprene)
    
    for z in [height - 0.05, height - 0.45]:
        union('cube', p=(0, 0, z), s=(length/2, width/2, 0.05),
            material=neoprene)

#########
# Scene #
#########

#sad_scorpion_attempt(name='Sad Scorpion Attempt', p=(30, 0, 0))
#sand_castle(name='Sand Castle', p=(10, 20, 0))
#cactus_drink(name='Cactus Drink', p=(40, 0, 0), original=True)
#cactus_drink_2(name='Cactus Drink 2', p=(40, 5, 0))
#blocky_racer(name='Racer', p=(50, 0, 0))
#helicarrier(name='Helicarrier', p=(60, 70, 0), mid_segments=1)
#gramorgan(name='Gramorgan', p=(40, 20, 0))
#circus_tent(name='Circus Test', p=(60, 20, 0))
#gazebo(name='Gazebo', p=(70, 0, 0))
#gate(name='Gate', p=(90, 0, 0))
#pinwheel_windmill(name='Pinwheel Windmill', p=(110, 0, 0), blades=20)
#lego_couch(name='Lego Couch', p=(120, 0, 0))
#tunnel('Tunnel', p=(140, 0, 0), width=12, height=8)
#lego_pear('Lego Pear', p=(160, 0, 0))
#pencil_tower('Pencil Tower', p=(180, 0, 0))
#geometry_crusher('Geometry Crusher', p=(200, 0, 0))
conveyor('Geometry Conveyor', p=(205, 0, 0), height=3, width=2.5, length=16)

# Unsolved problems:
# - How to select an individual vertex and move or merge it
# - How different material settings behave after export
