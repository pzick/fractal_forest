import bpy
from math import degrees, radians, sin, cos
from random import random, seed

DEBUG_PRINT = False
index = 0


def print_debug(s):
    if DEBUG_PRINT is True:
        print(s)


def branch(length, angle, depth, iterations, reduce, bend_angle, index_start, vertices, edges, faces):
    global index
    if depth > iterations:
        return -1
    curr_length = length
    curr_angle = angle
    edge_start = index_start

    # Add right branch
    x = vertices[edge_start][0]
    y = vertices[edge_start][1] + curr_length * sin(curr_angle + bend_angle)
    z = vertices[edge_start][2] + curr_length * cos(curr_angle + bend_angle)
    vertices.append((x, y, z))
    index += 1
    print_debug('--> depth: {}, edge_start: {}, index: {}, angle: {}, y: {}, z: {}'.format(depth, edge_start, index, degrees(curr_angle), y, z))
    curr_index = index
    edges.append([edge_start, index])

    print_debug('next right')
    branch(curr_length - reduce, curr_angle + bend_angle, depth + 1, iterations, reduce, bend_angle, curr_index, vertices, edges, faces)

    # Add left branch
    x = vertices[edge_start][0]
    y = vertices[edge_start][1] + curr_length * sin(curr_angle - bend_angle)
    z = vertices[edge_start][2] + curr_length * cos(curr_angle - bend_angle)
    vertices.append((x, y, z))
    index += 1
    print_debug('<-- depth: {}, edge_start: {}, index: {}, angle: {}, y: {}, z: {}'.format(depth, edge_start, index, degrees(curr_angle), y, z))
    curr_index = index
    edges.append([edge_start, index])
    
    print_debug('next left')
    branch(curr_length - reduce, curr_angle - bend_angle, depth + 1, iterations, reduce, bend_angle, curr_index, vertices, edges, faces)


def make_tree(angle, iterations, reduce, start_length, location):
    global index
    seed()
    bend_angle = radians(angle)
    vertices = [location]
    edges = []
    faces = []
    index = 0
    bend = 0

    print_debug('--------- start ------------')
    vertices.append((location[0], location[1], start_length + location[2]))
    index += 1
    edges.append([0, 1])

    # Build the tree mesh
    branch(start_length, 0, 0, iterations, reduce, bend_angle, index, vertices, edges, faces)

    new_mesh = bpy.data.meshes.new('new_mesh')
    new_mesh.from_pydata(vertices, edges, faces)
    new_mesh.update()

    new_object = bpy.data.objects.new('new_object', new_mesh)
    if 'new_collection' not in bpy.data.collections.keys():
        new_collection = bpy.data.collections.new('new_collection')
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections['new_collection']
    new_collection.objects.link(new_object)

    print_debug(new_object)
    if bpy.context.active_object is not None:
        bpy.context.active_object.select_set(False)
    bpy.context.view_layer.objects.active = None
    bpy.context.scene.objects[new_object.name].select_set(True)
    bpy.context.view_layer.objects.active = bpy.context.scene.objects[new_object.name]
    bpy.ops.object.convert(target='CURVE')
    new_object.data.bevel_depth = 0.2
    new_object.data.bevel_resolution = 6
    new_object.data.use_fill_caps = True

    # Only generate the material once, then reuse it for the other generated trees
    if 'Trees' not in bpy.data.materials.keys():
        mat = bpy.data.materials.new('Trees')
        mat.use_nodes = True
        mat.use_backface_culling = True
        mat.show_transparent_back = False
        mat.blend_method = 'OPAQUE'
        mat_nodes = mat.node_tree.nodes
        princ_bsdf = mat_nodes['Principled BSDF']
        
        princ_bsdf.inputs['Base Color'].default_value = 0.027, 0.326, 0.027, 1.0
        princ_bsdf.inputs['Specular'].default_value = 0.1
        princ_bsdf.inputs['Roughness'].default_value = 0.95

        color_ramp01 = mat_nodes.new(type='ShaderNodeValToRGB')
        color_ramp02 = mat_nodes.new(type='ShaderNodeValToRGB')
        obj_info = mat_nodes.new(type='ShaderNodeObjectInfo')
        mult_add = mat_nodes.new(type='ShaderNodeMath')
        hsl = mat_nodes.new(type='ShaderNodeHueSaturation')

        mult_add.operation = 'MULTIPLY_ADD'

        # Set up the color ramp for autumn colors (base color)
        color_ramp01.color_ramp.elements.new(0)
        color_ramp01.color_ramp.elements.new(0)
        color_ramp01.color_ramp.elements[0].color = 0.211, 0.005, 0, 1
        color_ramp01.color_ramp.elements[0].position = 0.123
        color_ramp01.color_ramp.elements[1].color = 0.655, 0.270, 0.043, 1
        color_ramp01.color_ramp.elements[1].position = 0.768
        color_ramp01.color_ramp.elements[2].color = 1.0, 0.858, 0.029, 1
        color_ramp01.color_ramp.elements[2].position = 0.864
        color_ramp01.color_ramp.elements[3].color = 0.200, 0.070, 0.011, 1
        color_ramp01.color_ramp.elements[3].position = 1.0

        # Set up the color ramp for spring colors (subsurface color)
        color_ramp02.color_ramp.elements[0].color = 0.008, 0.073, 0.008, 1
        color_ramp02.color_ramp.elements[0].position = 0.0
        color_ramp02.color_ramp.elements[1].color = 0, 0.5, 0, 1
        color_ramp02.color_ramp.elements[1].position = 1.0

        # Connect the shader nodes
        links = mat.node_tree.links
        links.new(obj_info.outputs['Random'], color_ramp01.inputs[0])
        links.new(obj_info.outputs['Random'], color_ramp02.inputs[0])
        links.new(obj_info.outputs['Random'], mult_add.inputs[0])
        links.new(mult_add.outputs[0], hsl.inputs[3])
        links.new(color_ramp01.outputs['Color'], hsl.inputs['Color'])
        links.new(hsl.outputs[0], princ_bsdf.inputs[0])
        links.new(color_ramp02.outputs['Color'], princ_bsdf.inputs[3])

        # Prettify the shader nodes layout
        obj_info.location = (-800, 110)
        mult_add.location = (-400, 350)
        color_ramp01.location = (-425, 110)
        color_ramp02.location = (-420, -170)
        hsl.location = (-55, 285)
        princ_bsdf.location = (250, 260)
        mat_nodes['Material Output'].location = (540, 260)
    else:
        mat = bpy.data.materials['Trees']
    new_object.data.materials.append(mat)
    print_debug('--------- end ------------')


def make_ground(scale, location):
    # Create a plane, scale and move it, name it 'Ground'
    bpy.ops.mesh.primitive_plane_add(location=location, scale=scale)
    ground = bpy.context.object
    ground.name = 'Ground'
    ground.scale = scale
    ground.location = location
    # Add a material and set the color
    if 'Ground' not in bpy.data.materials.keys():
        mat = bpy.data.materials.new('Ground')
        mat.use_nodes = True
        princ_bsdf = mat.node_tree.nodes['Principled BSDF']
        princ_bsdf.inputs['Base Color'].default_value = 0.039, 0.009, 0.007, 1.0
        princ_bsdf.inputs['Specular'].default_value = 0.0
        princ_bsdf.inputs['Roughness'].default_value = 1.0
    else:
        mat = bpy.data.materials['Ground']
    ground.data.materials.append(mat)

def clean():
    for m in bpy.data.materials:
        if m.name == 'Trees' or m.name == 'Ground':
            bpy.data.materials.remove(m)
    for obj in bpy.data.objects:
        if obj.name.find('new_obj') >= 0:
            bpy.data.objects.remove(obj)
        elif obj.name.find('Ground') == 0:
            bpy.data.objects.remove(obj)
    for m in bpy.data.meshes:
        if m.name.find('new_mesh') >= 0:
            bpy.data.meshes.remove(m)

# Remove any previously generated trees and associated materials
clean()

# Create a ground plane
make_ground((400, 400, 1), (0, 150, 0))

# Create 150 trees with randomized location, angles, and sizes
for tree in range(150):
    angle = random() * 20 + 10
    iterations = random() * 3 + 6
    start_x = random() * 300
    start_y = random() * 300
    make_tree(angle, iterations, 1, iterations, (start_x, start_y, 0))
