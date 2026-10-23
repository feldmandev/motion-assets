"""Post-load correction of the reviewed Pixel 10 Pro; never load/save the asset here.

Call calibrate_imported_pixel_front(profile, root, trace) after linking the imported
objects and applying finishes, before prepare_screen. Coordinates are root-local mm.
Exterior speaker-lip vertices follow the traced chassis; cavity interiors stay fixed.
"""
import math

MM = .001


def _body_outline(trace):
    points = trace['body_outline_mm']
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
    return [((x-cx)*72/(max(xs)-min(xs)), (y-cy)*152.8/(max(ys)-min(ys)))
            for x, y in points]


def _body_positions(vertices, outline):
    """Deform original rolled perimeter samples, leaving port interiors exact.

    Recover the original rounded-rectangle offset from its 11.8 mm corner and
    intersect that sample's outward normal with the corresponding traced offset.
    Z, connectivity, material assignments and UVs are never reconstructed.
    """
    from shapely.geometry import LineString, Polygon

    # The acceptance check also uses the convex envelope: one-pixel artwork
    # notches are not machined dents and can invert tiny existing cap triangles.
    polygon = Polygon(outline).convex_hull
    offsets = {}
    result = []
    for index, (x, y, z) in enumerate(vertices):
        original = (x, y, z)
        ox, oy = max(-24.2, min(24.2, x)), max(-64.6, min(64.6, y))
        dx, dy = x-ox, y-oy
        radius = math.hypot(dx, dy)
        inset = 11.8-radius
        roll_offset = .55-math.sqrt(max(0, .55**2-max(0, abs(z)-3.725)**2))
        # The source has 32 segments per quarter. Boolean intersections lie on
        # their chords, up to 11.8*(1-cos(pi/128)) = 0.003554 mm inside the circle.
        if radius == 0 or abs(inset-roll_offset) > .004:
            result.append(original)
            continue
        key = round(roll_offset, 5)
        if key not in offsets:
            offsets[key] = polygon.buffer(-key, quad_segs=24).exterior if key else polygon.exterior
        boundary = offsets[key]
        # Original slabs have only tangent endpoints on their long straight edges.
        # Slide those endpoints toward the new tangent, retaining exact W/H. Allow
        # 0.03 mm (less than one artwork pixel) for the skin's tiny side notches.
        # Otherwise a normal-only projection would inadvertently shrink the body.
        # Keep the bottom tangents' X coordinates: boolean cavity fans connect to
        # these samples, so sliding them along the bottom can reverse tiny faces.
        if ((y > 0 and abs(dx) < 1e-5 and abs(abs(x)-24.2) < 1e-5)
                or (abs(dy) < 1e-5 and abs(abs(y)-64.6) < 1e-5)):
            axis = 0 if abs(dy) < 1e-5 else 1
            target = boundary.bounds[axis+(2 if (x, y)[axis] > 0 else 0)]
            candidates = [p for p in boundary.coords if abs(p[axis]-target) < .03]
            nearest = min(candidates, key=lambda p: abs(p[1-axis]-(x, y)[1-axis]))
            # Leave one roll radius of straight-edge margin so the old cap's
            # tangent fan cannot overshoot the adjacent curved sample.
            along = math.copysign(max(0, abs(nearest[1-axis])-.55), nearest[1-axis])
            result.append((target, along, z) if axis == 0 else (along, target, z))
            continue
        ray = LineString([(ox, oy), (ox+20*dx/radius, oy+20*dy/radius)])
        hit = ray.intersection(boundary)
        assert hit.geom_type == 'Point', 'Trace offset must intersect the perimeter normal once'
        nx, ny = hit.coords[0]
        result.append((nx, ny, z))
    # Retain 1% of the original curvature so three old cap-ear triangles do not
    # become collinear on straight facets of the traced hull. This changes the
    # silhouette by micrometres; verify the full hull against the 0.10 mm gate.
    return [(x+.99*(nx-x), y+.99*(ny-y), z)
            for (x, y, z), (nx, ny, _) in zip(vertices, result)]


def calibrate_imported_pixel_front(profile, root, trace):
    """Only alter the imported body's perimeter and front glass.

    Antennas and selfie optics belong to the parent's common helpers. Other Pixel
    IDs are explicit no-ops. Returns measurements for the serialized build log.
    """
    if profile['id'] != 'pixel-10-pro' or 'asset' not in profile:
        return None
    import bpy
    from mathutils import Vector
    from geometry import slab, traced_ring
    from shapely.geometry import MultiPoint, Polygon

    assert trace and trace.get('body_outline_mm'), 'Measured Pixel 10 Pro trace required'
    assert not root.get('pixel_imported_front_calibrated'), 'Run once on a freshly loaded asset'
    assert tuple(profile['body_mm'][k] for k in ('width', 'height', 'depth')) == (72, 152.8, 8.6)
    names = ('Body | aluminum enclosure', 'Front glass | cover and equal bezel')
    body, glass = [bpy.data.objects[name] for name in names]
    for obj in (body, glass):
        assert obj.parent == root and tuple(obj.scale) == (1, 1, 1)
        assert all(abs(v) < 1e-8 for v in obj.rotation_euler)
        assert all(abs(obj.matrix_parent_inverse[i][j]-(i == j)) < 1e-8
                   for i in range(4) for j in range(4))
    assert all(abs(v) < 1e-8 for v in body.location)
    assert all(abs(v) < 1e-8 for v in glass.location[:2])
    assert not body.modifiers and not glass.modifiers

    outline = _body_outline(trace)
    before = [tuple(v.co) for v in body.data.vertices]
    body.data.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
    bounds = [max(p[i] for p in before)-min(p[i] for p in before) for i in range(3)]
    assert all(abs(a-b*MM) < 1e-7 for a, b in zip(bounds, (72, 152.8, 8.55)))
    after = _body_positions([tuple(c/MM for c in p) for p in before], outline)
    moved = 0
    for index, (vertex, old, new) in enumerate(zip(body.data.vertices, before, after)):
        if math.hypot(new[0]*MM-old[0], new[1]*MM-old[1]) > 1e-10:
            vertex.co.x, vertex.co.y = new[0]*MM, new[1]*MM
            moved += 1
    body.data.update()
    assert all(tuple(v.co) == old for v, old, new in zip(body.data.vertices, before, after)
               if tuple(c/MM for c in old) == new)
    assert all(v.co.z == old[2] for v, old in zip(body.data.vertices, before))
    for a, b, c in triangles:
        normal = (Vector(before[b])-Vector(before[a])).cross(Vector(before[c])-Vector(before[a]))
        if normal.length > 1e-12:
            new_normal = (body.data.vertices[b].co-body.data.vertices[a].co).cross(
                body.data.vertices[c].co-body.data.vertices[a].co)
            assert normal.dot(new_normal) > 0 and new_normal.length > 1e-15, 'Body triangle reversed or collapsed'
    actual_bounds = [max(v.co[i] for v in body.data.vertices)-min(v.co[i] for v in body.data.vertices)
                     for i in range(3)]
    assert all(abs(a-b) < 1e-7 for a, b in zip(actual_bounds, bounds))
    contour_error = MultiPoint([(v.co.x/MM, v.co.y/MM) for v in body.data.vertices]).convex_hull.exterior.hausdorff_distance(
        Polygon(outline).convex_hull.exterior)
    assert contour_error < .10, ('Enclosure differs from official contour', contour_error)

    # Keep the front-glass object, transforms, depth, Z centre and material identity.
    z0, z1 = min(v.co.z for v in glass.data.vertices), max(v.co.z for v in glass.data.vertices)
    assert abs((z1-z0)/MM-.30) < .001 and abs(z0+z1) < 1e-8
    glass_outline = traced_ring(outline, 1.30)
    temp = slab('Pixel 10 Pro | temporary calibrated glass', 69.4, 150.2, (z1-z0)/MM,
                10.3, (0, 0, 0), None, root, roll=.10, points=glass_outline)
    old = glass.data
    glass.data = temp.data
    for mat in old.materials:
        glass.data.materials.append(mat)
    bpy.data.objects.remove(temp, do_unlink=True)
    if old.users == 0:
        bpy.data.meshes.remove(old)
    assert all(abs((max(v.co[i] for v in glass.data.vertices)-min(v.co[i] for v in glass.data.vertices))/MM-size) < .001
               for i, size in enumerate((69.4, 150.2, .30)))

    root['pixel_imported_front_calibrated'] = True
    return {'body_vertices_moved': moved, 'unchanged_body_vertices': len(before)-moved,
            'body_contour_error_mm': contour_error, 'passes_0_10mm_contour_gate': contour_error < .10,
            'front_glass_inset_mm': 1.30}
