# The first Beldner script I wrote, now unused but preserved here

import bpy
import math

# Can't run this in edit mode
if bpy.context.active_object is not None:
    bpy.ops.object.mode_set(mode='OBJECT')

# Make sure nothing is selected
for object in bpy.context.selected_objects:
    object.select_set(False)

# Remove old object. Old meshes remain in memory, but won't be saved
if 'Sad Scorpion Attempt' in bpy.data.objects:
    bpy.data.objects['Sad Scorpion Attempt'].select_set(True)
    bpy.ops.object.delete()

# Actual mesh building goes here
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 30, 0), scale=(1.5, 2,
1))
base = bpy.context.active_object
base.name = 'Sad Scorpion Attempt' # Object name
base.data.name = 'Sad Scorpion Attempt' # Mesh name
for i in range(6):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(-4*math.sin(math.pi*i/6), 30, 4 + 4*math.cos(math.pi*i/6)), scale=(1.5, 1.4 + 0.1*i, 1))
    new_object = bpy.context.active_object
    
    # Sets bpy.context.active_object
    bpy.context.view_layer.objects.active = base
    
    booly = base.modifiers.new(name='booly', type='BOOLEAN')
    booly.object = new_object
    booly.operation = 'UNION'
    bpy.ops.object.modifier_apply(modifier='booly')
    
    # .delete() doesn't use the current value of bpy.context.active_object, so
    # it deletes new_object instead of base
    bpy.ops.object.delete()
