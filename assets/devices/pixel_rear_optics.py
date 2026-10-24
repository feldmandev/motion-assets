"""Procedural multi-layer 3D rear camera and flash optics for Pixel devices."""
import math
import bpy

from geometry import MM, disk, subtract

STEPS = 96


def _set_input(node, value, *names):
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def _build_iridescent_ar_glass(mat, palette='cyan_violet', roughness=0.012, reflect_min=0.055, reflect_max=0.42):
    """Build a thin-walled optical glass shader with strong angle-dependent thin-film AR color shift."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    out = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if out is None:
        return

    # Crystal-clear straight-through transmission (zero solid-glass milky TIR)
    trans = nodes.new('ShaderNodeBsdfTransparent')
    trans.inputs['Color'].default_value = (0.95, 0.97, 1.0, 1.0)

    # LayerWeight Facing drives both the thin-film interference color ramp and the reflection strength ramp
    layer = nodes.new('ShaderNodeLayerWeight')
    layer.inputs['Blend'].default_value = 0.35

    # Thin-film interference color spectrum across viewing angle + surface curvature
    color_ramp = nodes.new('ShaderNodeValToRGB')
    cr = color_ramp.color_ramp
    cr.interpolation = 'B_SPLINE'
    # Add 4 stops: 0.0 (normal incidence), 0.32 (mid-dome curvature), 0.62 (steep slope), 0.92 (grazing edge)
    while len(cr.elements) < 4:
        cr.elements.new(0.5)
    if palette == 'cyan_violet':
        # Main & periscope outer lens: deep sapphire/emerald center -> electric cyan -> cobalt blue -> vivid violet/magenta rim
        stops = [
            (0.00, (0.08, 0.92, 0.72, 1.0)),
            (0.32, (0.10, 0.68, 1.00, 1.0)),
            (0.64, (0.48, 0.22, 1.00, 1.0)),
            (0.92, (0.96, 0.20, 0.78, 1.0)),
        ]
    elif palette == 'violet_emerald':
        # Inner meniscus element 2: complementary magenta/violet center -> royal blue -> teal -> emerald/gold rim
        stops = [
            (0.00, (0.85, 0.18, 0.95, 1.0)),
            (0.35, (0.28, 0.32, 1.00, 1.0)),
            (0.68, (0.05, 0.88, 0.75, 1.0)),
            (0.95, (0.65, 0.98, 0.25, 1.0)),
        ]
    else:
        # Ultrawide outer lens: cobalt/cyan center -> royal violet -> magenta -> warm amber-rose rim
        stops = [
            (0.00, (0.10, 0.78, 1.00, 1.0)),
            (0.34, (0.34, 0.28, 1.00, 1.0)),
            (0.66, (0.88, 0.16, 0.86, 1.0)),
            (0.94, (1.00, 0.46, 0.22, 1.0)),
        ]
    for elem, (pos, col) in zip(cr.elements, stops):
        elem.position = pos
        elem.color = col

    # Primary sharp specular AR reflection lobe
    gloss_sharp = nodes.new('ShaderNodeBsdfGlossy')
    gloss_sharp.inputs['Roughness'].default_value = roughness
    links.new(layer.outputs['Facing'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], gloss_sharp.inputs['Color'])

    # Secondary broader colorful AR bloom/glare lobe around specular highlights
    gloss_bloom = nodes.new('ShaderNodeBsdfGlossy')
    gloss_bloom.inputs['Roughness'].default_value = min(0.14, roughness * 5.5)
    links.new(color_ramp.outputs['Color'], gloss_bloom.inputs['Color'])

    mix_gloss = nodes.new('ShaderNodeMixShader')
    mix_gloss.inputs['Fac'].default_value = 0.32
    links.new(gloss_sharp.outputs['BSDF'], mix_gloss.inputs[1])
    links.new(gloss_bloom.outputs['BSDF'], mix_gloss.inputs[2])

    # Reflection factor curve: keeps dark barrel contrast while giving vibrant colored glare across curved domes
    fac_ramp = nodes.new('ShaderNodeValToRGB')
    fac_ramp.color_ramp.elements[0].position = 0.0
    fac_ramp.color_ramp.elements[0].color = (reflect_min, reflect_min, reflect_min, 1.0)
    fac_ramp.color_ramp.elements[1].position = 0.88
    fac_ramp.color_ramp.elements[1].color = (reflect_max, reflect_max, reflect_max, 1.0)

    mix_final = nodes.new('ShaderNodeMixShader')
    links.new(layer.outputs['Facing'], fac_ramp.inputs['Fac'])
    links.new(fac_ramp.outputs['Color'], mix_final.inputs['Fac'])
    links.new(trans.outputs['BSDF'], mix_final.inputs[1])
    links.new(mix_gloss.outputs['Shader'], mix_final.inputs[2])
    links.new(mix_final.outputs['Shader'], out.inputs['Surface'])


def _make_material(name, base_rgb, metallic=0.0, roughness=0.3, ior=1.5,
                   specular=0.5, coat=0.0, coat_rough=0.05,
                   transmission=0.0, emission_rgb=None, emission_strength=0.0,
                   ar_palette=None, reflect_min=0.06, reflect_max=0.42):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (*base_rgb, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    _set_input(bsdf, ior, 'IOR')
    _set_input(bsdf, specular, 'Specular IOR Level', 'Specular')
    _set_input(bsdf, coat, 'Coat Weight', 'Clearcoat')
    _set_input(bsdf, coat_rough, 'Coat Roughness', 'Clearcoat Roughness')
    _set_input(bsdf, transmission, 'Transmission Weight', 'Transmission')
    if emission_rgb is not None and emission_strength > 0:
        _set_input(bsdf, (*emission_rgb, 1.0), 'Emission Color', 'Emission')
        _set_input(bsdf, emission_strength, 'Emission Strength')
    if ar_palette is not None:
        _build_iridescent_ar_glass(
            mat, palette=ar_palette, roughness=roughness,
            reflect_min=reflect_min, reflect_max=reflect_max
        )
    return mat


def _rear_materials():
    # Make 'Continuous clear optical cover' ultra-clear with a subtle sapphire-violet grazing edge glint
    cover = bpy.data.materials.get('Continuous clear optical cover')
    if cover and cover.use_nodes:
        _build_iridescent_ar_glass(
            cover, palette='cyan_violet', roughness=0.008,
            reflect_min=0.003, reflect_max=0.028
        )

    return {
        # Crisp dark gunmetal chamfered outer bezel ring
        'anodized_rim': _make_material(
            'Optical outer rim | original satin highlight',
            (0.003, 0.0035, 0.004), metallic=0, roughness=0.42, specular=0.03, coat=0
        ),
        # Machined inner barrel wall (deep dark anodized aluminum)
        'dark_barrel': _make_material(
            'Optical barrel | dark machined inner walls',
            (0.003, 0.0035, 0.004), metallic=0.2, roughness=0.4, specular=0.12
        ),
        # Concentric stepped baffle ridge lips that catch crisp thin metallic rim highlights
        'baffle_ridge': _make_material(
            'Pixel rear optics | baffle ridge',
            (0.045, 0.052, 0.065), metallic=0.86, roughness=0.19, specular=0.68
        ),
        # Precision internal lens retainer & aperture iris stop ring
        'iris_ring': _make_material(
            'Pixel rear optics | iris retainer ring',
            (0.085, 0.095, 0.115), metallic=0.94, roughness=0.14, specular=0.78
        ),
        # Deep light-absorbing matte baffle grooves
        'matte_well': _make_material(
            'Optical aperture | light-absorbing interior',
            (0.001, 0.0012, 0.0018), metallic=0.0, roughness=0.82, specular=0.03
        ),
        # Deep optical pupil / curved sapphire-coated sensor core with angle-dependent cyan/magenta sheen
        'deep_pupil': _make_material(
            'Pixel rear optics | deep sensor pupil',
            (0.0008, 0.0008, 0.001), metallic=0.05, roughness=0.55, ior=1.72,
            specular=0.015, coat=0
        ),
        # Outer & inner coated optical glass elements with multi-stop angle-dependent AR color shift
        'lens1_el1': _make_material(
            'Lens 1 | element 1 coating',
            (0.18, 0.56, 0.95), metallic=0.0, roughness=0.012, ior=1.54,
            specular=0.85, coat=0.55, coat_rough=0.010, transmission=0.92,
            ar_palette='cobalt_magenta', reflect_min=0.075, reflect_max=0.48
        ),
        'lens1_el2': _make_material(
            'Lens 1 | element 2 coating',
            (0.62, 0.20, 0.92), metallic=0.0, roughness=0.014, ior=1.58,
            specular=0.90, coat=0.65, coat_rough=0.012, transmission=0.88,
            ar_palette='violet_emerald', reflect_min=0.085, reflect_max=0.52
        ),
        'lens2_el1': _make_material(
            'Lens 2 | element 1 coating',
            (0.12, 0.72, 0.98), metallic=0.0, roughness=0.012, ior=1.54,
            specular=0.85, coat=0.55, coat_rough=0.010, transmission=0.92,
            ar_palette='cyan_violet', reflect_min=0.080, reflect_max=0.50
        ),
        'lens2_el2': _make_material(
            'Lens 2 | element 2 coating',
            (0.72, 0.18, 0.95), metallic=0.0, roughness=0.014, ior=1.58,
            specular=0.90, coat=0.65, coat_rough=0.012, transmission=0.88,
            ar_palette='violet_emerald', reflect_min=0.090, reflect_max=0.54
        ),
        'tele_el1': _make_material(
            'Telephoto | curved internal optical coating',
            (0.14, 0.68, 0.96), metallic=0.0, roughness=0.012, ior=1.54,
            specular=0.85, coat=0.55, coat_rough=0.010, transmission=0.92,
            ar_palette='cyan_violet', reflect_min=0.080, reflect_max=0.48
        ),
        'tele_prism': _make_material(
            'Telephoto | internal prism optic',
            (0.02, 0.08, 0.22), metallic=0.30, roughness=0.015, ior=1.70,
            specular=0.95, coat=1.0, coat_rough=0.008,
            emission_rgb=(0.05, 0.18, 0.42), emission_strength=0.10
        ),
        # Multi-layer 3D Flash materials
        'flash_reflector': _make_material(
            'Pixel rear flash | stepped metallic reflector',
            (0.78, 0.76, 0.72), metallic=0.92, roughness=0.15, specular=0.82
        ),
        'flash_warm_die': _make_material(
            'Pixel rear flash | warm phosphor LED die',
            (0.96, 0.72, 0.28), metallic=0.0, roughness=0.20,
            emission_rgb=(0.96, 0.74, 0.32), emission_strength=0.14
        ),
        'flash_cool_die': _make_material(
            'Pixel rear flash | cool phosphor surround',
            (0.90, 0.88, 0.80), metallic=0.0, roughness=0.22,
            emission_rgb=(0.90, 0.88, 0.80), emission_strength=0.07
        ),
        'flash_diffuser': _make_material(
            'flash',
            (0.88, 0.86, 0.78), metallic=0.0, roughness=0.03, ior=1.49,
            specular=0.65, coat=0.30, coat_rough=0.02, transmission=0.88,
            ar_palette='cyan_violet', reflect_min=0.03, reflect_max=0.18
        ),
    }


def _revolved_mesh(name, cx, cy, rings, materials, parent, steps=STEPS):
    """Build a revolved mesh around (cx, cy) with outward normals facing -Z."""
    if 'glass element' in name:
        apex = min(z for radius, z in rings)
        curvature = .55 if 'element 2' in name else .45
        rings = [(radius, apex+(z-apex)*curvature) for radius, z in rings]
    elif 'recessed barrel' in name:
        rings = [rings[i] for i in [0, 1, 3, 4, 11, 15, 18]]
        materials = [materials[i] for i in [0, 2, 3, 7, 14, 17]]
    vertices = []
    faces = []
    face_mats = []
    used_mats = []

    def mat_slot(mat):
        if mat not in used_mats:
            used_mats.append(mat)
        return used_mats.index(mat)

    ring_starts = []
    for r_mm, z_mm in rings:
        if r_mm <= 1e-6:
            ring_starts.append((len(vertices), True))
            vertices.append((cx * MM, cy * MM, z_mm * MM))
        else:
            ring_starts.append((len(vertices), False))
            for i in range(steps):
                a = 2.0 * math.pi * i / steps
                vertices.append(((cx + r_mm * math.cos(a)) * MM,
                                 (cy + r_mm * math.sin(a)) * MM,
                                 z_mm * MM))

    for band_idx, mat in enumerate(materials):
        s0, cap0 = ring_starts[band_idx]
        s1, cap1 = ring_starts[band_idx + 1]
        m_idx = mat_slot(mat)
        if not cap0 and not cap1:
            for i in range(steps):
                j = (i + 1) % steps
                faces.append((s0 + i, s1 + i, s1 + j, s0 + j))
                face_mats.append(m_idx)
        elif not cap0 and cap1:
            for i in range(steps):
                j = (i + 1) % steps
                faces.append((s0 + i, s1, s0 + j))
                face_mats.append(m_idx)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for mat in used_mats:
        mesh.materials.append(mat)
    for poly, m_idx in zip(mesh.polygons, face_mats):
        poly.material_index = m_idx
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def _rounded_rect_points(cx, cy, hw, hh, cr, z_mm, steps=STEPS):
    """Sample a rounded rectangle counter-clockwise in (x, y) with `steps` vertices."""
    cr = min(cr, hw - 1e-4, hh - 1e-4)
    corner_steps = steps // 4
    pts = []
    corners = [
        (hw - cr, hh - cr, 0.0, math.pi * 0.5),
        (-hw + cr, hh - cr, math.pi * 0.5, math.pi),
        (-hw + cr, -hh + cr, math.pi, math.pi * 1.5),
        (hw - cr, -hh + cr, math.pi * 1.5, math.pi * 2.0),
    ]
    for ox, oy, a0, a1 in corners:
        for k in range(corner_steps):
            t = k / corner_steps
            a = a0 + (a1 - a0) * t
            pts.append(((cx + ox + cr * math.cos(a)) * MM,
                        (cy + oy + cr * math.sin(a)) * MM,
                        z_mm * MM))
    return pts


def _lofted_rounded_rect(name, cx, cy, profiles, materials, parent, steps=STEPS, cap_end=False):
    """Loft concentric rounded-rectangle profiles [(hw, hh, cr, z_mm), ...]."""
    vertices = []
    faces = []
    face_mats = []
    used_mats = []

    def mat_slot(mat):
        if mat not in used_mats:
            used_mats.append(mat)
        return used_mats.index(mat)

    ring_starts = []
    for hw, hh, cr, z_mm in profiles:
        ring_starts.append(len(vertices))
        vertices.extend(_rounded_rect_points(cx, cy, hw, hh, cr, z_mm, steps))

    for band_idx, mat in enumerate(materials):
        s0 = ring_starts[band_idx]
        s1 = ring_starts[band_idx + 1]
        m_idx = mat_slot(mat)
        for i in range(steps):
            j = (i + 1) % steps
            faces.append((s0 + i, s1 + i, s1 + j, s0 + j))
            face_mats.append(m_idx)

    if cap_end and profiles:
        s_last = ring_starts[-1]
        _, _, _, z_last = profiles[-1]
        center_idx = len(vertices)
        vertices.append((cx * MM, cy * MM, z_last * MM))
        m_idx = mat_slot(materials[-1])
        for i in range(steps):
            j = (i + 1) % steps
            faces.append((s_last + i, center_idx, s_last + j))
            face_mats.append(m_idx)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for mat in used_mats:
        mesh.materials.append(mat)
    for poly, m_idx in zip(mesh.polygons, face_mats):
        poly.material_index = m_idx
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def _build_circular_camera(index, kind, lx, ly, lr, z_backing, max_depth, mats, parent):
    """Build a multi-layer 3D circular camera lens (stepped barrel + 2 curved glass domes + iris + pupil)."""
    prefix = 'Lens 2' if kind == 'main' else 'Lens 1'
    mat_el1 = mats['lens2_el1'] if kind == 'main' else mats['lens1_el1']
    mat_el2 = mats['lens2_el2'] if kind == 'main' else mats['lens1_el2']

    d = min(max_depth * 0.84, lr * 0.56 + 0.65)
    z0 = z_backing

    barrel_rings = [
        (lr * 1.03, z0 + 0.03),          # 0: under-backing flange
        (lr * 1.01, z0 - 0.025),         # 1: outer chamfered bezel lip
        (lr * 0.94, z0 - 0.020),         # 2: satin anodized bezel flat
        (lr * 0.90, z0 + 0.045),         # 3: inner bezel bevel
        (lr * 0.89, z0 + d * 0.16),      # 4: outer barrel vertical wall
        (lr * 0.82, z0 + d * 0.20),      # 5: concentric baffle step 1 (angled ridge)
        (lr * 0.81, z0 + d * 0.34),      # 6: baffle groove wall 1
        (lr * 0.74, z0 + d * 0.38),      # 7: concentric baffle step 2 (angled ridge)
        (lr * 0.73, z0 + d * 0.52),      # 8: baffle groove wall 2
        (lr * 0.65, z0 + d * 0.56),      # 9: machined inner lens retainer ring
        (lr * 0.60, z0 + d * 0.60),      # 10: inner retainer bevel
        (lr * 0.59, z0 + d * 0.76),      # 11: deep inner chamber wall
        (lr * 0.49, z0 + d * 0.80),      # 12: concentric baffle step 3
        (lr * 0.42, z0 + d * 0.84),      # 13: precision metallic iris stop ring
        (lr * 0.37, z0 + d * 0.90),      # 14: iris knife-edge bevel
        (lr * 0.36, z0 + d * 0.98),      # 15: deep pupil well wall
        (lr * 0.28, z0 + d * 0.92),      # 16: convex sensor pupil outer dome
        (lr * 0.16, z0 + d * 0.85),      # 17: convex sensor pupil mid dome
        (0.0,       z0 + d * 0.81),      # 18: convex sensor pupil apex
    ]
    barrel_mats = [
        mats['anodized_rim'],  # 0->1
        mats['anodized_rim'],  # 1->2
        mats['anodized_rim'],  # 2->3
        mats['dark_barrel'],   # 3->4
        mats['baffle_ridge'],  # 4->5
        mats['matte_well'],    # 5->6
        mats['baffle_ridge'],  # 6->7
        mats['dark_barrel'],   # 7->8
        mats['iris_ring'],     # 8->9
        mats['iris_ring'],     # 9->10
        mats['matte_well'],    # 10->11
        mats['baffle_ridge'],  # 11->12
        mats['iris_ring'],     # 12->13
        mats['iris_ring'],     # 13->14
        mats['matte_well'],    # 14->15
        mats['deep_pupil'],    # 15->16
        mats['deep_pupil'],    # 16->17
        mats['deep_pupil'],    # 17->18
    ]
    _revolved_mesh(
        f'Camera {index} | {prefix} | recessed barrel',
        lx, ly, barrel_rings, barrel_mats, parent
    )

    # 2. Curved outer convex glass element 1 (pronounced dome curvature so angle-dependent AR color shifts across the aperture)
    r_el1 = lr * 0.888
    z_el1_edge = z0 + d * 0.31
    z_el1_apex = z0 + 0.012
    sag1 = z_el1_edge - z_el1_apex
    el1_rings = []
    el1_steps = 12
    for k in range(el1_steps + 1):
        u = 1.0 - k / el1_steps
        r_k = r_el1 * u
        z_k = z_el1_apex + sag1 * (u * u)
        el1_rings.append((r_k, z_k))
    _revolved_mesh(
        f'Camera {index} | {prefix} | glass element 1',
        lx, ly, el1_rings, [mat_el1] * el1_steps, parent
    )

    # 3. Recessed curved meniscus inner glass element 2 (steeper inner dome for secondary violet/emerald double-reflex)
    r_el2 = lr * 0.588
    z_el2_edge = z0 + d * 0.76
    z_el2_apex = z0 + d * 0.44
    sag2 = z_el2_edge - z_el2_apex
    el2_rings = []
    el2_steps = 10
    for k in range(el2_steps + 1):
        u = 1.0 - k / el2_steps
        r_k = r_el2 * u
        z_k = z_el2_apex + sag2 * (u * u)
        el2_rings.append((r_k, z_k))
    _revolved_mesh(
        f'Camera {index} | {prefix} | glass element 2',
        lx, ly, el2_rings, [mat_el2] * el2_steps, parent
    )


def _build_periscope_camera(index, lx, ly, lr, z_backing, max_depth, mats, parent):
    """Build a multi-layer 3D rounded-rectangular periscope telephoto camera assembly."""
    hw0 = lr * 1.58 * 0.5
    hh0 = lr * 2.10 * 0.5
    cr0 = lr * 0.46
    d = min(max_depth * 0.84, lr * 0.62 + 0.70)
    z0 = z_backing

    def scaled(s, z_val):
        return (hw0 * s, hh0 * s, max(0.15, cr0 * s), z_val)

    barrel_profiles = [
        scaled(1.03, z0 + 0.03),         # 0: under-backing flange
        scaled(1.01, z0 - 0.025),        # 1: chamfered outer bezel lip
        scaled(0.93, z0 - 0.020),        # 2: satin bezel flat
        scaled(0.89, z0 + 0.05),         # 3: inner bezel bevel
        scaled(0.88, z0 + d * 0.20),     # 4: outer rectangular barrel wall
        scaled(0.80, z0 + d * 0.25),     # 5: rectangular baffle step 1
        scaled(0.79, z0 + d * 0.44),     # 6: middle barrel wall
        scaled(0.71, z0 + d * 0.49),     # 7: rectangular baffle step 2
        scaled(0.70, z0 + d * 0.68),     # 8: lower barrel wall
        scaled(0.62, z0 + d * 0.73),     # 9: precision inner prism frame
        scaled(0.58, z0 + d * 0.96),     # 10: deep periscope sensor cavity
    ]
    barrel_mats = [
        mats['anodized_rim'],  # 0->1
        mats['anodized_rim'],  # 1->2
        mats['anodized_rim'],  # 2->3
        mats['dark_barrel'],   # 3->4
        mats['baffle_ridge'],  # 4->5
        mats['matte_well'],    # 5->6
        mats['baffle_ridge'],  # 6->7
        mats['dark_barrel'],   # 7->8
        mats['iris_ring'],     # 8->9
        mats['matte_well'],    # 9->10
    ]
    _lofted_rounded_rect(
        f'Camera {index} | Telephoto | open rectangular periscope barrel',
        lx, ly, barrel_profiles, barrel_mats, parent, cap_end=True
    )

    # 2. Curved rectangular outer optical element
    el_profiles = []
    el_steps = 10
    z_edge = z0 + d * 0.32
    z_apex = z0 + 0.012
    for k in range(el_steps):
        u = 1.0 - k / el_steps
        s = 0.875 * u
        z_k = z_apex + (z_edge - z_apex) * (u * u)
        el_profiles.append(scaled(s, z_k))
    _lofted_rounded_rect(
        f'Camera {index} | Telephoto | curved inner optical element',
        lx, ly, el_profiles, [mats['tele_el1']] * (len(el_profiles) - 1), parent, cap_end=True
    )

    # 3. Internal angled periscope prism element
    pw = hw0 * 0.54
    ph = hh0 * 0.56
    z_prism_front = z0 + d * 0.48
    z_prism_back = z0 + d * 0.86
    nx, ny = 8, 12
    p_verts = []
    p_faces = []
    for iy in range(ny + 1):
        ty = iy / ny
        y_pos = (ly - ph + 2.0 * ph * ty) * MM
        arch = math.sin(ty * math.pi) * 0.12
        z_row = z_prism_front + (z_prism_back - z_prism_front) * (0.25 + 0.5 * ty) - arch
        for ix in range(nx + 1):
            tx = ix / nx
            x_pos = (lx - pw + 2.0 * pw * tx) * MM
            x_arch = math.sin(tx * math.pi) * 0.10
            p_verts.append((x_pos, y_pos, (z_row - x_arch) * MM))
    for iy in range(ny):
        for ix in range(nx):
            i0 = iy * (nx + 1) + ix
            i1 = i0 + 1
            i2 = i0 + (nx + 1) + 1
            i3 = i0 + (nx + 1)
            p_faces.append((i0, i3, i2, i1))
    prism_mesh = bpy.data.meshes.new(f'Camera {index} | Telephoto | deep sensor well')
    prism_mesh.from_pydata(p_verts, [], p_faces)
    prism_mesh.materials.append(mats['tele_prism'])
    for poly in prism_mesh.polygons:
        poly.use_smooth = True
    prism_mesh.update()
    prism_obj = bpy.data.objects.new(f'Camera {index} | Telephoto | deep sensor well', prism_mesh)
    bpy.context.scene.collection.objects.link(prism_obj)
    prism_obj.parent = parent


def _build_flash_module(index, fx, fy, fr, z_backing, max_depth, mats, parent):
    """Build a multi-layer 3D LED flash (chamfered bezel + stepped silver reflector + dual-tone die + Fresnel lens)."""
    d = min(max_depth * 0.55, fr * 0.42 + 0.35)
    z0 = z_backing

    cup_rings = [
        (fr * 1.03, z0 + 0.02),          # 0: under-backing flange
        (fr * 1.00, z0 - 0.020),         # 1: outer chamfered bezel lip
        (fr * 0.92, z0 - 0.015),         # 2: bezel flat
        (fr * 0.89, z0 + 0.04),          # 3: inner bezel drop
        (fr * 0.82, z0 + d * 0.28),      # 4: parabolic reflector step 1
        (fr * 0.78, z0 + d * 0.30),      # 5: reflector micro-ledge 1
        (fr * 0.68, z0 + d * 0.54),      # 6: parabolic reflector step 2
        (fr * 0.64, z0 + d * 0.56),      # 7: reflector micro-ledge 2
        (fr * 0.52, z0 + d * 0.80),      # 8: parabolic reflector step 3
        (fr * 0.46, z0 + d * 0.86),      # 9: LED package cavity rim
        (fr * 0.44, z0 + d * 0.78),      # 10: raised LED phosphor package edge
        (fr * 0.25, z0 + d * 0.76),      # 11: cool-white outer phosphor zone
        (fr * 0.22, z0 + d * 0.74),      # 12: warm-amber central phosphor die edge
        (0.0,       z0 + d * 0.72),      # 13: warm-amber die center
    ]
    cup_mats = [
        mats['anodized_rim'],     # 0->1
        mats['anodized_rim'],     # 1->2
        mats['anodized_rim'],     # 2->3
        mats['flash_reflector'],  # 3->4
        mats['flash_reflector'],  # 4->5
        mats['flash_reflector'],  # 5->6
        mats['flash_reflector'],  # 6->7
        mats['flash_reflector'],  # 7->8
        mats['flash_reflector'],  # 8->9
        mats['flash_reflector'],  # 9->10
        mats['flash_cool_die'],   # 10->11
        mats['flash_cool_die'],   # 11->12
        mats['flash_warm_die'],   # 12->13
    ]
    _revolved_mesh(
        f'Flash {index} | reflector and dual-tone emitter',
        fx, fy, cup_rings, cup_mats, parent, steps=72
    )

    r_lens = fr * 0.895
    fresnel_rings = [
        (r_lens * 1.00, z0 + 0.03),
        (r_lens * 0.92, z0 - 0.008),
        (r_lens * 0.82, z0 - 0.015),
        (r_lens * 0.78, z0 + 0.005),
        (r_lens * 0.64, z0 - 0.018),
        (r_lens * 0.60, z0 + 0.002),
        (r_lens * 0.44, z0 - 0.022),
        (r_lens * 0.40, z0 - 0.002),
        (r_lens * 0.22, z0 - 0.025),
        (0.0,           z0 - 0.028),
    ]
    _revolved_mesh(
        f'Flash {index}',
        fx, fy, fresnel_rings, [mats['flash_diffuser']] * (len(fresnel_rings) - 1), parent, steps=72
    )


def enhance_pixel_rear_optics(profile):
    """Replace flat/squashed rear camera & flash meshes on Pixel models with deep 3D multi-layer assemblies."""
    if not str(profile.get('id', '')).startswith('pixel-'):
        return
    if 'camera' not in profile:
        return

    spec = profile['camera']
    if spec.get('local_pupil'):
        return

    parent = bpy.data.objects.get(profile['name'])
    if parent is None:
        return

    body = profile['body_mm']
    back_z = -body['depth'] / 2.0
    bump = spec['bump_mm']
    face_z = back_z - bump
    well_z = (face_z + 0.04) if spec.get('integrated_plateau') else (back_z - 0.02)

    for obj in list(bpy.data.objects):
        if obj.name.startswith('Camera ') and ' | ' in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.name.startswith('Flash '):
            bpy.data.objects.remove(obj, do_unlink=True)

    mats = _rear_materials()
    windows = spec.get('windows', [])

    for index, lens in enumerate(spec.get('lenses', [])):
        win_idx = lens.get('window', 0)
        window_face_z = back_z if win_idx in spec.get('body_windows', []) else face_z
        window_optical_z = window_face_z - spec.get('optical_bump_mm', 0.0)
        z_backing = window_optical_z + 0.14
        max_depth = max(1.2, (well_z - z_backing) - 0.08)
        lx, ly = lens['center_mm']
        lr = lens['radius_mm']
        if lens['kind'] == 'periscope':
            _build_periscope_camera(index, lx, ly, lr, z_backing, max_depth, mats, parent)
        else:
            _build_circular_camera(index, lens['kind'], lx, ly, lr, z_backing, max_depth, mats, parent)

    for index, flash in enumerate(spec.get('flash', [])):
        fx, fy, fr = flash
        flash_surface_z = back_z if spec.get('flash_surface') == 'body' else face_z
        flash_z = flash_surface_z - spec.get('flash_offset_mm', 0.0) + 0.14
        for win_idx, win in enumerate(windows):
            wx, wy, ww, wh, _ = win
            if abs(fx - wx) < (ww * 0.5 - fr * 0.5) and abs(fy - wy) < (wh * 0.5 - fr * 0.5):
                backing = bpy.data.objects.get(f'Black optical backing {win_idx}')
                if backing is not None:
                    window_face_z = back_z if win_idx in spec.get('body_windows', []) else face_z
                    window_optical_z = window_face_z - spec.get('optical_bump_mm', 0.0)
                    flash_z = window_optical_z + 0.14
                    hole = disk('Flash opening tool', fx, fy, flash_z, fr * 1.01, 0.6, None, parent)
                    subtract(backing, hole)
                break
        max_depth = max(1.0, (well_z - flash_z) - 0.08)
        _build_flash_module(index, fx, fy, fr, flash_z, max_depth, mats, parent)
