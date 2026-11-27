"""Lecture ciblée d'un instantané .blend NON compressé écrit par le worker 5.2.

Le writer regroupe les blocs DATA d'un ID Action après son en-tête AC.
Les offsets ne sont utilisés qu'après qualification des structures SDNA.
Le module ne suit aucune adresse et ne lit jamais la mémoire de Blender.
"""
from struct import error as StructError, Struct, unpack_from

HEADER = b"BLENDER17-01v0502"
BLOCK = Struct("<4siQQq")
LAYER_FIELDS = (
    ("char", "name[64]"), ("float", "influence"), ("uchar", "layer_flags"),
    ("int8_t", "layer_mix_mode"), ("uchar", "_pad0[2]"),
    ("ActionStrip", "**strip_array"), ("int", "strip_array_num"), ("uchar", "_pad1[4]"),
)
STRIP_FIELDS = (
    ("int8_t", "strip_type"), ("uchar", "_pad0[3]"), ("int", "data_index"),
    ("float", "frame_start"), ("float", "frame_end"), ("float", "frame_offset"), ("uchar", "_pad1[4]"),
)
ID_PREFIX = (
    ("void", "*next"), ("void", "*prev"), ("ID", "*newid"), ("Library", "*lib"),
    ("AssetMetaData", "*asset_data"), ("char", "name[258]"),
)
ACTION_PREFIX = (("ID", "id"), ("ActionLayer", "**layer_array"), ("int", "layer_array_num"))


def _blocks(stream, size):
    stream.seek(len(HEADER))
    while True:
        code, dna, _, length, count = BLOCK.unpack(stream.read(BLOCK.size))
        offset = stream.tell()
        if length > size - offset:
            raise ValueError("Bloc Blender tronqué")
        yield code, dna, count, length
        stream.seek(offset + length)
        if code == b"ENDB":
            return


def _structures(dna):
    cursor = 0

    def tag(value):
        nonlocal cursor
        if dna[cursor:cursor + 4] != value:
            raise ValueError("Schéma Blender non reconnu")
        cursor += 4

    def strings(value):
        nonlocal cursor
        tag(value)
        count, = unpack_from("<I", dna, cursor)
        cursor += 4
        values = []
        for _ in range(count):
            end = dna.index(b"\0", cursor)
            values.append(dna[cursor:end].decode("ascii"))
            cursor = end + 1
        cursor = (cursor + 3) & ~3
        return values

    tag(b"SDNA")
    names = strings(b"NAME")
    types = strings(b"TYPE")
    tag(b"TLEN")
    sizes = unpack_from(f"<{len(types)}H", dna, cursor)
    cursor = (cursor + 2 * len(types) + 3) & ~3
    tag(b"STRC")
    count, = unpack_from("<I", dna, cursor)
    cursor += 4
    structures = {}
    for index in range(count):
        type_index, field_count = unpack_from("<HH", dna, cursor)
        cursor += 4
        fields = []
        for _ in range(field_count):
            type_id, name_id = unpack_from("<HH", dna, cursor)
            cursor += 4
            fields.append((types[type_id], names[name_id]))
        structures[types[type_index]] = (index, sizes[type_index], tuple(fields))
    return structures


def action_states(path):
    """Associe chaque nom d'action qualifiable à ses octets privés."""
    try:
        with path.open("rb") as stream:
            if stream.read(len(HEADER)) != HEADER:
                return {}
            size = path.stat().st_size
            dna = next(
                (stream.read(length) for code, _, _, length in _blocks(stream, size)
                 if code == b"DNA1" and length <= 4 * 1024 * 1024),
                b"",
            )
            schema = _structures(dna)
            _, id_size, id_fields = schema["ID"]
            action_index, action_size, action_fields = schema["bAction"]
            layer_index, layer_size, layer_fields = schema["ActionLayer"]
            strip_index, strip_size, strip_fields = schema["ActionStrip"]
            if (
                id_fields[:len(ID_PREFIX)] != ID_PREFIX
                or action_fields[:len(ACTION_PREFIX)] != ACTION_PREFIX
                or (layer_size, layer_fields) != (88, LAYER_FIELDS)
                or (strip_size, strip_fields) != (24, STRIP_FIELDS)
                or id_size < 298 or action_size < id_size + 12
            ):
                return {}

            states = {}
            name = None
            for code, type_index, count, length in _blocks(stream, size):
                if code == b"AC\0\0":
                    name = None
                    if (type_index, count, length) == (action_index, 1, action_size):
                        data = stream.read(length)
                        layer_count, = unpack_from("<i", data, id_size + 8)
                        if data[40:42] == b"AC" and layer_count == 1:
                            name = data[42:298].split(b"\0", 1)[0].decode("utf-8")
                            if name in states:
                                return {}
                            states[name] = [[], []]
                elif code != b"DATA":
                    name = None
                elif name is not None:
                    if (type_index, count, length) == (layer_index, 1, layer_size):
                        data = stream.read(length)
                        if unpack_from("<i", data, 80) == (1,):
                            states[name][0].append(data[64:70].hex())
                    elif (type_index, count, length) == (strip_index, 1, strip_size):
                        data = stream.read(length)
                        states[name][1].append(data[4:20].hex())
            return {
                name: (layers[0], strips[0])
                for name, (layers, strips) in states.items() if len(layers) == len(strips) == 1
            }
    except (OSError, ValueError, KeyError, IndexError, StructError):
        return {}
