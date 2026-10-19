from copy import deepcopy
from itertools import product
from math import radians, tan
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from fontTools import subset
from fontTools.merge import Merger
from fontTools.merge.cmap import computeMegaGlyphOrder
from fontTools.merge.options import Options as MergeOptions
from fontTools.merge.util import first, onlyExisting
from fontTools.misc.fixedTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib.instancer import AxisTriple, instantiateVariableFont
from fontTools.varLib.models import VariationModel


ROOT = Path(__file__).resolve().parent
GOOGLE_PATH = ROOT / "GoogleSansFlex-VariableFont_GRAD,ROND,opsz,slnt,wdth,wght.ttf"
FREDOKA_PATH = ROOT / "Fredoka-VariableFont_wdth,wght.ttf"
OUTPUT_PATH = ROOT / "FeldmanFont.ttf"

VARIABLE_TABLES = {"avar", "cvar", "fvar", "gvar", "HVAR", "MVAR", "STAT", "VVAR"}
TARGET_AXES = ["opsz", "wdth", "wght", "GRAD", "ROND", "slnt"]

# Calibrated from aggregate Google Sans Flex outline and advance changes.
GRADE_WEIGHT_SHIFT = 67.0
SMALL_OPSZ_WEIGHT_SHIFT = 21.0
LARGE_OPSZ_WEIGHT_SHIFT = -26.0
SMALL_OPSZ_WIDTH_SCALE = 1.1475591716
LARGE_OPSZ_WIDTH_SCALE = 0.911
SMALL_OPSZ_HEIGHT_SCALE = 1.0394444444
CONDENSED_WIDTH_SCALE = 0.83
EXPANDED_WIDTH_SCALE = 1.31
CONDENSED_LARGE_OPSZ_INTERACTION_SCALE = 0.758
SLANT_SHEAR = tan(radians(10))
TERMINAL_MAX_SPAN = 0.18
TERMINAL_MIN_BULGE = 0.22
TERMINAL_MAX_DIRECTION_DOT = -0.45
TERMINAL_MIN_STEM_RATIO = 1.25
TERMINAL_MAX_CHORD_DOT = 0.35
MANUAL_TERMINAL_CAPS = {
    "uni05E4": [(25, 31, list(range(25, 32)))],
    "uni05E3": [(18, 23, list(range(18, 24)))],
}

# The Fredoka subset has no local variation store when merged. Its new GPOS
# VariationIndex records refer to regions appended to Google Sans's GDEF store.
otTables.VarStore.mergeMap = {"*": onlyExisting(first)}


def subset_to_missing_characters(font, unicodes):
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.notdef_glyph = True
    options.notdef_outline = True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)


def source_name_map(google_order, fredoka_order, original_fredoka_order):
    orders = [list(google_order), list(fredoka_order)]
    computeMegaGlyphOrder(SimpleNamespace(), orders)
    return dict(zip(original_fredoka_order, orders[1]))


def normalized_locations():
    locations = []
    for wght, wdth, opsz, grade, roundness, slnt in product(
        (-1.0, 0.0, 1.0),
        (-1.0, 0.0, 1.0),
        (-1.0, 0.0, 1.0),
        (0.0, 1.0),
        (0.0, 1.0),
        (-1.0, 0.0),
    ):
        location = {
            "wght": wght,
            "wdth": wdth,
            "opsz": opsz,
            "GRAD": grade,
            "ROND": roundness,
            "slnt": slnt,
        }
        locations.append({tag: value for tag, value in location.items() if value})
    return locations


def iter_gpos_anchors(font, include_objects=False):
    if "GPOS" not in font:
        return
    lookups = font["GPOS"].table.LookupList.Lookup
    for lookup_index, lookup in enumerate(lookups):
        for subtable_index, subtable in enumerate(lookup.SubTable):
            lookup_type = lookup.LookupType
            if lookup_type == 9:
                lookup_type = subtable.ExtensionLookupType
                subtable = subtable.ExtSubTable

            prefix = (lookup_index, subtable_index, lookup_type)
            if lookup_type == 4:
                for glyph, record in zip(
                    subtable.MarkCoverage.glyphs, subtable.MarkArray.MarkRecord
                ):
                    anchor = record.MarkAnchor
                    if anchor is not None:
                        yield prefix + ("mark", glyph, record.Class), glyph, anchor
                for glyph, record in zip(
                    subtable.BaseCoverage.glyphs, subtable.BaseArray.BaseRecord
                ):
                    for class_index, anchor in enumerate(record.BaseAnchor):
                        if anchor is not None:
                            yield prefix + ("base", glyph, class_index), glyph, anchor
            elif lookup_type == 5:
                for glyph, record in zip(
                    subtable.MarkCoverage.glyphs, subtable.MarkArray.MarkRecord
                ):
                    anchor = record.MarkAnchor
                    if anchor is not None:
                        yield prefix + ("mark", glyph, record.Class), glyph, anchor
                for glyph, attach in zip(
                    subtable.LigatureCoverage.glyphs,
                    subtable.LigatureArray.LigatureAttach,
                ):
                    for component_index, component in enumerate(attach.ComponentRecord):
                        for class_index, anchor in enumerate(component.LigatureAnchor):
                            if anchor is not None:
                                yield (
                                    prefix
                                    + ("ligature", glyph, component_index, class_index),
                                    glyph,
                                    anchor,
                                )
            elif lookup_type == 6:
                for glyph, record in zip(
                    subtable.Mark1Coverage.glyphs, subtable.Mark1Array.MarkRecord
                ):
                    anchor = record.MarkAnchor
                    if anchor is not None:
                        yield prefix + ("mark1", glyph, record.Class), glyph, anchor
                for glyph, record in zip(
                    subtable.Mark2Coverage.glyphs, subtable.Mark2Array.Mark2Record
                ):
                    for class_index, anchor in enumerate(record.Mark2Anchor):
                        if anchor is not None:
                            yield prefix + ("mark2", glyph, class_index), glyph, anchor


def anchor_values(font):
    return {
        key: (glyph, float(anchor.XCoordinate), float(anchor.YCoordinate))
        for key, glyph, anchor in iter_gpos_anchors(font)
    }


class FredokaAxisSynthesizer:
    def __init__(self, font):
        self.font = font
        self.glyph_order = font.getGlyphOrder()
        self.instances = {}
        self.controls = {}
        self.terminal_caps = {}
        glyf = font["glyf"]
        metrics = font["hmtx"].metrics
        for glyph_name in self.glyph_order:
            coordinates, controls = glyf._getCoordinatesAndControls(
                glyph_name, metrics
            )
            self.controls[glyph_name] = controls
            self.terminal_caps[glyph_name] = self.find_terminal_caps(
                coordinates, controls, font["head"].unitsPerEm
            )
            self.terminal_caps[glyph_name].extend(
                MANUAL_TERMINAL_CAPS.get(glyph_name, [])
            )

    @staticmethod
    def find_terminal_caps(coordinates, controls, units_per_em):
        if controls.numberOfContours <= 0:
            return []

        def length(vector):
            return (vector[0] ** 2 + vector[1] ** 2) ** 0.5

        def subtract(first, second):
            return first[0] - second[0], first[1] - second[1]

        caps = []
        contour_start = 0
        maximum_span = units_per_em * TERMINAL_MAX_SPAN
        for contour_end in controls.endPts:
            on_curve = [
                index
                for index in range(contour_start, contour_end + 1)
                if controls.flags[index] & 1
            ]
            if len(on_curve) < 5:
                contour_start = contour_end + 1
                continue

            for position in range(len(on_curve)):
                previous = on_curve[(position - 1) % len(on_curve)]
                start = on_curve[position]
                middle = on_curve[(position + 1) % len(on_curve)]
                end = on_curve[(position + 2) % len(on_curve)]
                following = on_curve[(position + 3) % len(on_curve)]

                chord = subtract(coordinates[end], coordinates[start])
                chord_length = length(chord)
                if not chord_length or chord_length > maximum_span:
                    continue

                start_to_middle = subtract(coordinates[middle], coordinates[start])
                projection = (
                    start_to_middle[0] * chord[0]
                    + start_to_middle[1] * chord[1]
                ) / (chord_length * chord_length)
                projected = (
                    coordinates[start][0] + projection * chord[0],
                    coordinates[start][1] + projection * chord[1],
                )
                bulge = length(subtract(coordinates[middle], projected))
                if bulge < chord_length * TERMINAL_MIN_BULGE:
                    continue

                incoming = subtract(coordinates[start], coordinates[previous])
                outgoing = subtract(coordinates[following], coordinates[end])
                incoming_length = length(incoming)
                outgoing_length = length(outgoing)
                if not incoming_length or not outgoing_length:
                    continue
                if min(incoming_length, outgoing_length) < (
                    chord_length * TERMINAL_MIN_STEM_RATIO
                ):
                    continue
                direction_dot = (
                    incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
                ) / (incoming_length * outgoing_length)
                if direction_dot > TERMINAL_MAX_DIRECTION_DOT:
                    continue
                incoming_chord_dot = abs(
                    incoming[0] * chord[0] + incoming[1] * chord[1]
                ) / (incoming_length * chord_length)
                outgoing_chord_dot = abs(
                    outgoing[0] * chord[0] + outgoing[1] * chord[1]
                ) / (outgoing_length * chord_length)
                if max(incoming_chord_dot, outgoing_chord_dot) > (
                    TERMINAL_MAX_CHORD_DOT
                ):
                    continue

                path = [start]
                index = start
                while index != end:
                    index = contour_start if index == contour_end else index + 1
                    path.append(index)
                caps.append((start, end, path))

            contour_start = contour_end + 1
        return caps

    @staticmethod
    def source_weight(normalized):
        return {-1.0: 300.0, 0.0: 400.0, 1.0: 700.0}[normalized]

    @staticmethod
    def source_width(normalized):
        return {-1.0: 75.0, 0.0: 100.0, 1.0: 125.0}[normalized]

    def _load_instance(self, weight, width):
        key = (round(weight, 6), round(width, 6))
        if key not in self.instances:
            instance = instantiateVariableFont(
                self.font,
                {"wght": weight, "wdth": width},
                inplace=False,
            )
            glyf = instance["glyf"]
            metrics = instance["hmtx"].metrics
            coordinates = {}
            for glyph_name in self.glyph_order:
                coords, _ = glyf._getCoordinatesAndControls(glyph_name, metrics)
                coordinates[glyph_name] = GlyphCoordinates(coords)
            self.instances[key] = (coordinates, anchor_values(instance))
        return self.instances[key]

    def _interpolation_pair(self, weight):
        if weight < 300:
            return 300.0, 400.0, (weight - 300.0) / 100.0
        if weight > 700:
            return 600.0, 700.0, (weight - 600.0) / 100.0
        return weight, weight, 0.0

    def raw_coordinates(self, glyph_name, weight, width):
        lower, upper, scalar = self._interpolation_pair(weight)
        first = self._load_instance(lower, width)[0][glyph_name]
        if lower == upper:
            return GlyphCoordinates(first)
        second = self._load_instance(upper, width)[0][glyph_name]
        return first + (second - first) * scalar

    def raw_anchor(self, anchor_key, weight, width):
        lower, upper, scalar = self._interpolation_pair(weight)
        first = self._load_instance(lower, width)[1][anchor_key]
        if lower == upper:
            return first[1], first[2]
        second = self._load_instance(upper, width)[1][anchor_key]
        return (
            first[1] + (second[1] - first[1]) * scalar,
            first[2] + (second[2] - first[2]) * scalar,
        )

    def parameters(self, glyph_name, location):
        base_weight = self.source_weight(location.get("wght", 0.0))
        normalized_width = location.get("wdth", 0.0)
        width = self.source_width(normalized_width)
        opsz = location.get("opsz", 0.0)
        grade = location.get("GRAD", 0.0)
        roundness = location.get("ROND", 0.0)
        slant = location.get("slnt", 0.0)

        if opsz < 0:
            optical_weight_shift = -opsz * SMALL_OPSZ_WEIGHT_SHIFT
            x_scale = 1 + -opsz * (SMALL_OPSZ_WIDTH_SCALE - 1)
            y_scale = 1 + -opsz * (SMALL_OPSZ_HEIGHT_SCALE - 1)
        else:
            optical_weight_shift = opsz * LARGE_OPSZ_WEIGHT_SHIFT
            x_scale = 1 + opsz * (LARGE_OPSZ_WIDTH_SCALE - 1)
            y_scale = 1.0

        if normalized_width < 0:
            x_scale *= 1 + -normalized_width * (CONDENSED_WIDTH_SCALE - 1)
        else:
            x_scale *= 1 + normalized_width * (EXPANDED_WIDTH_SCALE - 1)
        if normalized_width < 0 and opsz > 0:
            interaction = -normalized_width * opsz
            x_scale *= 1 + interaction * (
                CONDENSED_LARGE_OPSZ_INTERACTION_SCALE - 1
            )

        effective_weight = (
            base_weight + grade * GRADE_WEIGHT_SHIFT + optical_weight_shift
        )
        effective = self.raw_coordinates(glyph_name, effective_weight, width)
        base = self.raw_coordinates(glyph_name, base_weight, width)

        effective_advance = effective[-3][0] - effective[-4][0]
        base_advance = base[-3][0] - base[-4][0]
        desired_advance = base_advance * x_scale

        real_effective = effective[:-4]
        real_base = base[:-4]
        if effective_advance or base_advance:
            source_center = effective_advance / 2
            target_center = desired_advance / 2
        else:
            source_center = (
                (min(x for x, _ in real_effective) + max(x for x, _ in real_effective))
                / 2
                if real_effective
                else 0
            )
            target_center = (
                (min(x for x, _ in real_base) + max(x for x, _ in real_base)) / 2
                if real_base
                else 0
            )

        return {
            "effective": effective,
            "desired_advance": desired_advance,
            "source_center": source_center,
            "target_center": target_center,
            "x_scale": x_scale,
            "y_scale": y_scale,
            "shear": -slant * SLANT_SHEAR,
            "roundness": roundness,
            "effective_weight": effective_weight,
            "width": width,
        }

    @staticmethod
    def transform_point(x, y, params):
        y *= params["y_scale"]
        x = (
            (x - params["source_center"]) * params["x_scale"]
            + params["target_center"]
        )
        x += params["shear"] * y
        return x, y

    def coordinates(self, glyph_name, location):
        params = self.parameters(glyph_name, location)
        source = params["effective"]
        result = GlyphCoordinates(
            [self.transform_point(x, y, params) for x, y in source[:-4]]
            + list(source[-4:])
        )
        result[-4] = (0, result[-4][1])
        result[-3] = (params["desired_advance"], result[-3][1])
        return self.apply_roundness(glyph_name, result, params["roundness"])

    def apply_roundness(self, glyph_name, coordinates, roundness):
        controls = self.controls[glyph_name]
        if controls.numberOfContours <= 0:
            return coordinates

        square_amount = 1.0 - roundness
        if not square_amount:
            return coordinates

        squared = GlyphCoordinates(coordinates)
        for start, end, path in self.terminal_caps[glyph_name]:
            start_point = coordinates[start]
            chord = (
                coordinates[end][0] - start_point[0],
                coordinates[end][1] - start_point[1],
            )
            chord_length_squared = chord[0] ** 2 + chord[1] ** 2
            if not chord_length_squared:
                continue
            normal = (-chord[1], chord[0])
            outer_offset = max(
                (
                    (coordinates[index][0] - start_point[0]) * normal[0]
                    + (coordinates[index][1] - start_point[1]) * normal[1]
                    for index in path
                ),
                key=abs,
            )
            for index in path:
                point = coordinates[index]
                relative = (point[0] - start_point[0], point[1] - start_point[1])
                offset = relative[0] * normal[0] + relative[1] * normal[1]
                distance = (outer_offset - offset) / chord_length_squared
                projected = (
                    point[0] + distance * normal[0],
                    point[1] + distance * normal[1],
                )
                squared[index] = (
                    point[0] + (projected[0] - point[0]) * square_amount,
                    point[1] + (projected[1] - point[1]) * square_amount,
                )
        return squared

    def anchor(self, anchor_key, glyph_name, location):
        params = self.parameters(glyph_name, location)
        x, y = self.raw_anchor(
            anchor_key, params["effective_weight"], params["width"]
        )
        return self.transform_point(x, y, params)


def support_regions(store, target_axes, supports):
    region_indices = []
    for support in supports:
        region = otTables.VarRegion()
        region.VarRegionAxis = []
        for tag in target_axes:
            start, peak, end = support.get(tag, (0.0, 0.0, 0.0))
            axis = otTables.VarRegionAxis()
            axis.StartCoord = start
            axis.PeakCoord = peak
            axis.EndCoord = end
            region.VarRegionAxis.append(axis)
        region_indices.append(len(store.VarRegionList.Region))
        store.VarRegionList.Region.append(region)
    store.VarRegionList.RegionCount = len(store.VarRegionList.Region)
    return region_indices


def append_var_data(store, target_axes, supports, items):
    region_indices = support_regions(store, target_axes, supports)
    var_data = otTables.VarData()
    var_data.VarRegionIndex = region_indices
    var_data.VarRegionCount = len(region_indices)
    var_data.Item = items
    var_data.ItemCount = len(items)
    var_data.NumShorts = len(region_indices)
    outer_index = len(store.VarData)
    store.VarData.append(var_data)
    store.VarDataCount = len(store.VarData)
    return outer_index


def variation_device(outer_index, inner_index):
    device = otTables.Device()
    device.StartSize = outer_index
    device.EndSize = inner_index
    device.DeltaFormat = 0x8000
    return device


def round_coordinates(coordinates):
    coordinates.toInt()
    return coordinates


def synthesize_glyph_variations(synthesizer, model, locations):
    supports = [support for support in model.supports if support]
    glyph_variations = {}
    width_items = []

    for glyph_name in synthesizer.glyph_order:
        masters = [
            synthesizer.coordinates(glyph_name, location) for location in locations
        ]
        master_widths = [coords[-3][0] - coords[-4][0] for coords in masters]
        deltas = model.getDeltas(masters, round=round_coordinates)
        width_deltas = model.getDeltas(master_widths, round=otRound)

        variations = []
        item = []
        for support, delta, width_delta in zip(
            model.supports, deltas, width_deltas
        ):
            if not support:
                continue
            item.append(width_delta)
            if any(x or y for x, y in delta):
                variations.append(TupleVariation(deepcopy(support), list(delta)))
        glyph_variations[glyph_name] = variations
        width_items.append(item)

    return glyph_variations, width_items, supports


def set_static_default_outlines(font, synthesizer):
    glyph_order = font.getGlyphOrder()
    if len(glyph_order) != len(synthesizer.glyph_order):
        raise ValueError("Fredoka glyph order changed while creating static outlines")

    glyf = font["glyf"]
    for source_name, static_name in zip(synthesizer.glyph_order, glyph_order):
        controls = synthesizer.controls[source_name]
        if controls.numberOfContours <= 0:
            continue
        coordinates = synthesizer.coordinates(source_name, {})
        glyph = glyf[static_name]
        glyph.coordinates = GlyphCoordinates(coordinates[:-4])
        glyph.flags = bytearray(controls.flags)
        glyph.endPtsOfContours = list(controls.endPts)
        glyph.removeHinting()


def add_anchor_variations(
    google, fredoka_static, synthesizer, model, locations, supports
):
    anchor_records = list(iter_gpos_anchors(fredoka_static))
    items = []
    attachments = []

    for anchor_key, glyph_name, anchor in anchor_records:
        masters = [
            synthesizer.anchor(anchor_key, glyph_name, location)
            for location in locations
        ]
        x_deltas = model.getDeltas([point[0] for point in masters], round=otRound)
        y_deltas = model.getDeltas([point[1] for point in masters], round=otRound)
        x_item = [delta for support, delta in zip(model.supports, x_deltas) if support]
        y_item = [delta for support, delta in zip(model.supports, y_deltas) if support]

        for attribute, item in (("XDeviceTable", x_item), ("YDeviceTable", y_item)):
            if any(item):
                attachments.append((anchor, attribute, len(items)))
                items.append(item)

    if not items:
        return

    store = google["GDEF"].table.VarStore
    outer_index = append_var_data(store, TARGET_AXES, supports, items)
    for anchor, attribute, inner_index in attachments:
        anchor.Format = 3
        if not hasattr(anchor, "XDeviceTable"):
            anchor.XDeviceTable = None
        if not hasattr(anchor, "YDeviceTable"):
            anchor.YDeviceTable = None
        setattr(anchor, attribute, variation_device(outer_index, inner_index))


def add_hvar_variations(hvar, names, glyph_order, supports, width_items):
    store = hvar.table.VarStore
    outer_index = append_var_data(store, TARGET_AXES, supports, width_items)
    mapping = hvar.table.AdvWidthMap.mapping
    for inner_index, old_name in enumerate(glyph_order):
        mapping[names[old_name]] = (outer_index << 16) | inner_index


def rename_font(font):
    replacements = {
        0: (
            "Copyright 2015 Google LLC. All Rights Reserved. "
            "Copyright 2016 The Fredoka Project Authors "
            "(https://github.com/hafontia/Fredoka-One). "
            "Modifications Copyright 2026 Feldman."
        ),
        1: "Feldman Font",
        3: "1.000;FELD;FeldmanFont-Regular",
        4: "Feldman Font Regular",
        5: "Version 1.000",
        6: "FeldmanFont-Regular",
        8: "Feldman",
        9: "Google Sans Authors and Fredoka Project Authors; modified by Feldman",
        25: "FeldmanFont",
    }
    for record in font["name"].names:
        replacement = replacements.get(record.nameID)
        if replacement is None:
            replacement = record.toUnicode().replace("GoogleSansFlex", "FeldmanFont")
        record.string = replacement.encode(record.getEncoding())

    font["name"].names = [
        record for record in font["name"].names if record.nameID not in {11, 12}
    ]
    description = (
        "Feldman Font is a modified typeface based on Google Sans Flex and "
        "Fredoka. It is licensed under the SIL Open Font License, Version 1.1, "
        "and is not affiliated with or endorsed by Google LLC or the Fredoka "
        "Project Authors."
    )
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        font["name"].setName(
            "Feldman Font", 16, platform_id, encoding_id, language_id
        )
        font["name"].setName("Regular", 17, platform_id, encoding_id, language_id)
        font["name"].setName(
            description, 10, platform_id, encoding_id, language_id
        )

    font["head"].fontRevision = 1.0
    font["OS/2"].achVendID = "FELD"


def main():
    print("Preparing source fonts", flush=True)
    google = TTFont(GOOGLE_PATH)
    fredoka = TTFont(FREDOKA_PATH)

    google_cmap = google.getBestCmap()
    fredoka_cmap = fredoka.getBestCmap()
    missing_unicodes = sorted(set(fredoka_cmap) - set(google_cmap))

    fredoka = instantiateVariableFont(
        fredoka,
        {"wght": AxisTriple(300, 400, 700)},
        inplace=False,
    )
    for glyph_name in fredoka.getGlyphOrder():
        fredoka["gvar"].variations.setdefault(glyph_name, [])
    scale_upem(fredoka, google["head"].unitsPerEm)
    subset_to_missing_characters(fredoka, missing_unicodes)

    locations = normalized_locations()
    model = VariationModel(
        locations,
        axisOrder=["wght", "wdth", "opsz", "GRAD", "ROND", "slnt"],
    )
    synthesizer = FredokaAxisSynthesizer(fredoka)

    print("Synthesizing Fredoka axis masters", flush=True)
    glyph_variations, width_items, supports = synthesize_glyph_variations(
        synthesizer, model, locations
    )

    with TemporaryDirectory(prefix=".merge-fonts-", dir=ROOT) as temp_dir:
        temp_dir = Path(temp_dir)
        fredoka_variable_path = temp_dir / "fredoka-variable-subset.ttf"
        fredoka_static_path = temp_dir / "fredoka-static-subset.ttf"
        google_path = temp_dir / "google.ttf"

        fredoka.save(fredoka_variable_path)
        fredoka_static = instantiateVariableFont(
            TTFont(fredoka_variable_path),
            {"wght": 400, "wdth": 100},
            inplace=False,
        )
        set_static_default_outlines(fredoka_static, synthesizer)
        add_anchor_variations(
            google, fredoka_static, synthesizer, model, locations, supports
        )

        fredoka_static.save(fredoka_static_path)
        google.save(google_path)

        names = source_name_map(
            google.getGlyphOrder(),
            fredoka_static.getGlyphOrder(),
            synthesizer.glyph_order,
        )

        merge_options = MergeOptions()
        merge_options.drop_tables = sorted(VARIABLE_TABLES)
        print("Merging outlines and layout", flush=True)
        merged = Merger(options=merge_options).merge(
            [str(google_path), str(fredoka_static_path)]
        )

    print("Restoring variable tables", flush=True)
    for tag in VARIABLE_TABLES - {"gvar", "HVAR"}:
        if tag in google:
            merged[tag] = deepcopy(google[tag])

    merged["gvar"] = deepcopy(google["gvar"])
    for old_name, variations in glyph_variations.items():
        merged["gvar"].variations[names[old_name]] = variations

    merged["HVAR"] = deepcopy(google["HVAR"])
    add_hvar_variations(
        merged["HVAR"], names, synthesizer.glyph_order, supports, width_items
    )

    rename_font(merged)
    print("Saving output", flush=True)
    merged.save(OUTPUT_PATH)

    print(f"Wrote {OUTPUT_PATH.name}")
    print(f"Added {len(missing_unicodes)} Unicode characters from Fredoka")
    print("Fredoka glyph axes: wdth, wght, opsz, GRAD, ROND, slnt")


if __name__ == "__main__":
    main()
