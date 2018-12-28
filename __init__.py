# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Rotation Constrained",
    "author": "Ryan Southall",
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "category": "Mesh"}


import bpy, math, mathutils, bmesh, numpy

class MESH_OT_rotation_constrained(bpy.types.Operator):
    """Rotation with constrained vertices"""
    bl_idname = "mesh.rotation_constrained"
    bl_label = "Rotation Constrained"
    bl_options = {'REGISTER', 'UNDO'}

# Colons now required in 2.8 as properties are now fields
    raxis: bpy.props.EnumProperty(
            items=[("0", "X", "Rotate around X-axis"),
                   ("1", "Y", "Rotate around Y-axis"),
                   ("2", "Z", "Rotate around Z-axis"),
                   ],
            name="Rotation Axis",
            description="Specify the axis of rotation",
            default="1")

    caxis: bpy.props.EnumProperty(
            items=[("0", "X", "Constrain to X-axis"),
                   ("1", "Y", "Constrain to Y-axis"),
                   ("2", "Z", "Constrain to Z-axis"),
                   ],
            name="Constraint Axis",
            description="Specify the vertex constraint axis",
            default="2")

    rpoint: bpy.props.EnumProperty(
            items=[("0", "Mid", "Rotate the end face around its midpoint"),
                   ("1", "Max", "Rotate the end face around its highpoint"),
                   ("2", "Min", "Rotate the end face around its lowpoint"),
                   ],
            name="Rotation point",
            description="Specify the point on the end face to rotate around",
            default="0")

    rmirror: bpy.props.BoolProperty(name="Mirror:", default = 0)

    rdeg: bpy.props.FloatProperty(name="Degrees", default = 0, min = -120, max = 120)

    def invoke(self, context, event):
        self.bmesh = bmesh.from_edit_mesh(context.active_object.data)
        bmfaces = [face for face in self.bmesh.faces if face.select]
        self.norm_z = numpy.sum([face.normal for face in bmfaces], axis = 0)/len(bmfaces)
        self.norm_y = numpy.sum([face.calc_tangent_edge() for face in bmfaces], axis = 0)/len(bmfaces)
        self.norm_x = numpy.sum([-face.normal.cross(-face.calc_tangent_edge()) for face in bmfaces], axis = 0)/len(bmfaces)
        bpy.ops.object.editmode_toggle()
        self.mesh = context.active_object.data
        self.omw = context.active_object.matrix_world.copy()
        self.oml = context.active_object.matrix_local.copy()
        self.omwi = self.omw.inverted()
        bpy.ops.object.editmode_toggle()
        return self.execute(context)

    def execute(self, context):
        if self.rdeg != 0 and self.caxis != self.raxis:
            bpy.ops.object.editmode_toggle()
            posaxis = mathutils.Vector([(0, 1)[paxis not in (self.raxis, self.caxis)] for paxis in ("0", "1", "2")])
            posindex = list(posaxis).index(1)
            caxis = [(0, 1)[i == int(self.caxis)] for i in range(3)]
            faces = [face for face in self.mesh.polygons if face.select == True]
           
            for face in faces:
                if self.mesh.polygons.active == face.index:
                    faces.insert(0, faces.pop(faces.index(face)))
                    
            vertlists = [[self.mesh.vertices[fv] for fv in face.vertices] for face in faces]

            for vl, vertlist in enumerate(vertlists):                
                for v in vertlist:
                    if context.scene.transform_orientation_slots[0].type == 'LOCAL':
                        vmax = max([v.co[posindex] for v in vertlist])
                        vmin = min([v.co[posindex] for v in vertlist])
                        refpos = ((vmin+vmax)/2, vmax, vmin)[int(self.rpoint)]
                        v.co += mathutils.Vector((v.co[posindex] - refpos) * mathutils.Vector((caxis)) * math.tan(float((-1, 1)[(vl > 0) * (self.rmirror)] * self.rdeg) * 0.0174533))

                    elif context.scene.transform_orientation_slots[0].type == 'NORMAL':
                        local_caxis = (self.norm_x, self.norm_y, self.norm_z)[int(self.caxis)]
                        local_posaxis = (self.norm_x, self.norm_y, self.norm_z)[posindex]
                        vmax = max([v.co.dot(mathutils.Vector(local_posaxis)) for v in vertlist])
                        vmin = min([v.co.dot(mathutils.Vector(local_posaxis)) for v in vertlist])
                        refpos = ((vmin+vmax)/2, vmax, vmin)[int(self.rpoint)]
                        v.co += mathutils.Vector((v.co.dot(mathutils.Vector(local_posaxis)) - refpos) * mathutils.Vector(local_caxis) * math.tan(float((-1, 1)[(vl > 0) * (self.rmirror)] * self.rdeg)*0.0174533))

                    elif context.scene.transform_orientation_slots[0].type == 'GLOBAL':
                        vmax = max([(self.omw@v.co)[posindex] for v in vertlist])
                        vmin = min([(self.omw@v.co)[posindex] for v in vertlist])
                        refpos = ((vmin+vmax)/2, vmax, vmin)[int(self.rpoint)]
                        v.co += mathutils.Vector(((self.omw@v.co)[posindex] - refpos) * mathutils.Vector((caxis)) * math.tan(float((-1, 1)[(vl > 0) * (self.rmirror)] * self.rdeg)*0.0174533))@self.omwi

            bpy.ops.object.editmode_toggle()

        return {'FINISHED'}


addon_keymaps = []
classes = (MESH_OT_rotation_constrained,)

def register():
    for cl in classes:
        bpy.utils.register_class(cl)
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new("mesh.rotation_constrained", 'R', 'PRESS', alt=True, shift=True)
    kmi.properties.rdeg = 0
    addon_keymaps.append(km)

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    del addon_keymaps[:]


