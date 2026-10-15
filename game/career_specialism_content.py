"""Authored fictional career specialisms; materials are per complete output unit.

This is game content, not medical, legal or safety-critical operating guidance.
Agency inputs represent organizational supplies, never the worker's income.
The runtime reads packaged JSON only. Public accessors return detached JSON
structures; the internal recursively frozen catalogue cannot be mutated.
"""
from pathlib import Path
from types import MappingProxyType

import hashlib
import json


CAREER_IDS = (
    "mother_baby",
    "pharmacy",
    "accounting",
    "customer_care",
    "teacher",
    "tour_guide",
    "milk_tea",
    "restaurant",
    "cafe_bakery",
    "florist",
    "grocery",
    "repair",
    "farm",
    "delivery",
    "homestay",
    "pet_care",
    "salon",
    "corp_accounting",
    "tax_payroll",
    "group_accounting",
    "clothing",
    "pet_shop",
    "tra_da",
    "fruit",
    "garbage",
    "drain",
    "homemaker",
    "ice_cream",
    "nail",
    "pagoda",
    "pho",
    "com",
    "photobooth",
    "giupviec",
    "naucom",
    "babysitter",
    "library",
    "pilot",
    "flight_attendant",
    "oil",
    "hr_admin",
    "secretary",
    "it_helpdesk",
    "railway",
    "nurse",
    "lighthouse",
    "rescue",
    "lifeguard",
    "police",
    "zpop",
    "art_studio",
    "lawyer",
    "laundry",
    "post_office",
    "customs",
)
_FILES = (
    "career_specialisms.json",
    "career_specialisms_21_37.json",
    "career_specialisms_38_54.json",
    "career_specialisms_55.json",
)
_PACK_KEYS = {"tier", "title", "output_unit", "inputs", "procedure", "check"}
_INPUT_KEYS = {"name", "unit", "quantity", "unit_cost"}
_CHECK_KEYS = {"prompt", "good", "bad", "why"}
# Frozen approval fingerprints, authored from the approved catalogue once.
# No documentation files are consulted at runtime.
_TITLE_DIGESTS = {
    "mother_baby": "cf02eaf620b1ceafeeb8f6c1604fe4541438a2e1444564530e0d12dd47c44c65",
    "pharmacy": "2ffde982584e1544a6e7d8e18e19fec5499daf94c9aaca359bf876041d7592ab",
    "accounting": "b39d3a0b0fb9763b4b59bdf3c6cf5409113ad83e2ee23f21e89d62dee8251454",
    "customer_care": "68346d238a934a1856fd2a1eae14e76da33e53c34792e51bd4c4ab19c33c8d41",
    "teacher": "c1799b69b0e14fcda61bdb1f6cd74e6588843aaa4f29ecae928f04c87295d791",
    "tour_guide": "b79be985a8c6c2c73af16f95fc5479a46105d48c0de49778ee8f3bd5df7cd016",
    "milk_tea": "94ef8ca969acf1c4ddadb22c0dadc5619b4440cdaacfdfbe3cf1a1aee14d8d2d",
    "restaurant": "a7e98b640217d05dc14485fe2ec3ce1c623b15f675c2bbb3cfe529e8e2be795b",
    "cafe_bakery": "b9002b4c8b8fcee5222c4346606f4633f046b6304cb2405ac496f5bf8fc511f4",
    "florist": "a8eafe45685aa9238a671c83fdcb9c52a3104d4e0fae7a8623c2de905cddf617",
    "grocery": "55fb7527df886a36e365a6594d041ea41dbb364fee40a2e44764af7280fc42ff",
    "repair": "8c9e77b84284e6897de1502fbc77a167523aac3ab3b23ac5bbf46249b87823bb",
    "farm": "2eee6aaa9ebbb35ba63cd50dd7a9b2f3ad3d4ae9747b5c091f5efcf18d1e3687",
    "delivery": "962995577d27a9242b681c539cdc8884b203e0f4d975e862fb320692b8f5a36d",
    "homestay": "7b1364eb266fb9e1260832698f0c9dc032dfa1fd735de4284a83667788866293",
    "pet_care": "421e5110dd5225cf2c2c7371c82deb695352925e00a9a006105b6126975cf09f",
    "salon": "8e0c0efdb949a5afd367cd68e9806abe029446a78234069d8f8f0efdf02933a4",
    "corp_accounting": "bea99abd75bd36783ff45734e10b79d814590a7720a9f022c94f3296a854ca0d",
    "tax_payroll": "81a7c6907834d6f3b92a35e1554bbd2d20cd83870c38c5cb3b809a3e50376b80",
    "group_accounting": "c8948fe0c4d3be684ac7b56295e6e18f12b73b667880aa7103e65d82ee52bdd8",
    "clothing": "c82186196f5b9f6c7fbdb9afc64338a73c1ac4378936476a311d8bd7264431d5",
    "pet_shop": "dd3ab91b967badd1c86043f6591f68bacaa01902741eca585d6946ba1e722e5b",
    "tra_da": "598c64bbd9cd9c7f2cdd3f3bc2ea722bfb0ec166d35ee9a6a519b731077562d5",
    "fruit": "696c12700005b122177eff5944a210373723bd97b4e40472cd8a10f5d8a62890",
    "garbage": "8c84f1a33362fab0c9f625600a84902119abf91ae1865965310d7ad4e3cd3793",
    "drain": "e220bbd50dec0f534a2e333dfb6ad0b48dbf9ed1e1d9ebd44b3a07586a6b4cfc",
    "homemaker": "47514e971311619a7dc56b3a6628e5c489efe1389890906658596b82aa4250e6",
    "ice_cream": "f9a676aaf08df69fca419b58ef3afce4a7072bb1160b6733ba98361568738b99",
    "nail": "47b210efc9261e8f591d9aded4e6346a821a1833ffe01429b79d3be529866ac7",
    "pagoda": "68519e92fc544c3bd0473732c40779ffcbde493f18f3cd03f784d0f8702af7b1",
    "pho": "60626a7203791a12217e25f14fe1f73da788302ed2ee80f4e0b449a4bb7ac1bb",
    "com": "3b42f8a3309ecb0a2c7f85fe8a804f98d49ff70d803091d88564d0570677d938",
    "photobooth": "60245fdbccc92faf6e5ffccfbfa492adf164e441e140ca0a4f6a97d3b2a9eaea",
    "giupviec": "36e5f2708d33dc7b4db780f4c133459c816675a09b7ed12b73337def8d49bb89",
    "naucom": "011b69fc7040f82027086bf323c74a872fc8d6d6c2d21595d3a0084b6c887cf6",
    "babysitter": "0c35db0778359834c5a05a06d1d76c6307961232c862c54b30836c1bcf796f09",
    "library": "9f1c19c98ca1dc21cec36715647196845ad3e5ef617fb9398dd106fbbda334e2",
    "pilot": "065241bdd279349a13a50b2353582a1625d6961b8da1860192af21029363106e",
    "flight_attendant": "724121d9ac600685aea52588a45c89f0051d5c8fa47e3b558396095dbe19e1c7",
    "oil": "b78210e344d10206f9c8aee1fda458e51c4c39539b925649e36ee5bd18bafa2e",
    "hr_admin": "d5264b68fa5b208777573edc5ba03975b0ac025e8e64997bfdc0d7dbaa586702",
    "secretary": "d9b7316aaee588456398caa8274184dfaeda52f0763aa2240d1ccfcb199ab40c",
    "it_helpdesk": "b5fc30bbda1a862836c3b2aaa7b1da0880d75bee90d9206fa0b88ffe0ac15f6c",
    "railway": "c2ca0bc54948f1980df41230efcc6ee261364be10ea1e534b84a6b53ab4abdd1",
    "nurse": "a9f933e225e0ddb15ab6f14155c2ca43193a8f7f0a8581c62512830fe81f4a70",
    "lighthouse": "83eb36e5daf1afe39cf9c1b2c6fe9274e5cd166879b2a0a17f2dc3422aa8d07d",
    "rescue": "d801bc91ed5df20d6d47390278cdebb18e67e1f5dece8da4c63767f216aa4f17",
    "lifeguard": "6a4eb72cd1c5c3ec13f61b46cf9af6d7087e323807af9152733d8cc99688632e",
    "police": "5e6377791f6c09e35e4ce74ee6a6553dd4a2ed290a96f68f3bb7b2b955a737be",
    "zpop": "d2b89ce8c4e4f7fccef74f63ec5cfd1458ecbb4b852001258a9d762b8986d7d2",
    "art_studio": "96afdb97afacd4e7ab94b40e6baf9ff8775a138990cf9884582551b6a93e2f43",
    "lawyer": "cc027551027175b75beed974cfbecc76dda6a9e7f63815e6f8a413ab15a16278",
    "laundry": "efcff125b236f98b659d54509de1a4149683e0e8b30360c4dd2bfc457b3aaf74",
    "customs": "a09f24b274c73db1cddd38eb50fa34cea34f8847dd22a483fc803445ae276f49",
    "post_office": "2e15eb95dcac32a33c4edc12ac71ed905086b6b2021ddea28b0c7be4c9f92c67",
}


def _text(value, context):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError(f"Invalid catalogue text: {context}")
    return value


def validate_catalogue(catalogue):
    """Reject incomplete, ambiguous or malformed content before publishing it."""
    if not isinstance(catalogue, dict) or set(catalogue) != set(CAREER_IDS):
        raise ValueError("Catalogue must contain exactly the expected career registry")
    all_titles, all_procedures, all_checks = set(), set(), set()
    for cid, items in catalogue.items():
        if not isinstance(items, list) or len(items) != 10:
            raise ValueError(f"{cid}: exactly ten packs required")
        for tier, item in enumerate(items, 1):
            if not isinstance(item, dict) or set(item) != _PACK_KEYS:
                raise ValueError(f"{cid}/{tier}: invalid pack fields")
            if type(item["tier"]) is not int or item["tier"] != tier:
                raise ValueError(f"{cid}/{tier}: invalid ordered tier")
            title = _text(item["title"], f"{cid}/{tier}/title")
            _text(item["output_unit"], f"{cid}/{tier}/output_unit")
            if title in all_titles:
                raise ValueError(f"Duplicate pack title: {title}")
            all_titles.add(title)
            inputs = item["inputs"]
            if not isinstance(inputs, list) or not 1 <= len(inputs) <= 2:
                raise ValueError(f"{cid}/{tier}: one or two inputs required")
            names, cost = set(), 0
            for material in inputs:
                if not isinstance(material, dict) or set(material) != _INPUT_KEYS:
                    raise ValueError(f"{cid}/{tier}: invalid input fields")
                name = _text(material["name"], f"{cid}/{tier}/input/name")
                _text(material["unit"], f"{cid}/{tier}/input/unit")
                if name in names:
                    raise ValueError(f"{cid}/{tier}: repeated input")
                names.add(name)
                for key in ("quantity", "unit_cost"):
                    if type(material[key]) is not int or not 0 < material[key] <= 100000:
                        raise ValueError(f"{cid}/{tier}: invalid input {key}")
                cost += material["quantity"] * material["unit_cost"]
            if cost > 100000:
                raise ValueError(f"{cid}/{tier}: input cost exceeds game ceiling")
            procedure = item["procedure"]
            if (not isinstance(procedure, list) or len(procedure) != 3
                    or not all(isinstance(step, str) for step in procedure)):
                raise ValueError(f"{cid}/{tier}: three textual steps required")
            for step in procedure:
                _text(step, f"{cid}/{tier}/procedure")
            sequence = tuple(procedure)
            if len(set(sequence)) != 3 or sequence in all_procedures:
                raise ValueError(f"{cid}/{tier}: distinct authored sequence required")
            all_procedures.add(sequence)
            check = item["check"]
            if not isinstance(check, dict) or set(check) != _CHECK_KEYS:
                raise ValueError(f"{cid}/{tier}: invalid acceptance fields")
            for key, value in check.items():
                _text(value, f"{cid}/{tier}/check/{key}")
            evidence = (check["good"], check["bad"])
            if evidence[0] == evidence[1] or evidence in all_checks:
                raise ValueError(f"{cid}/{tier}: distinct acceptance evidence required")
            all_checks.add(evidence)
        approved = hashlib.sha256("\n".join(p["title"] for p in items).encode("utf-8")).hexdigest()
        if approved != _TITLE_DIGESTS.get(cid):
            raise ValueError(f"{cid}: titles differ from the approved catalogue")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Repeated JSON key: {key}")
        result[key] = value
    return result


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _detach(value):
    if isinstance(value, MappingProxyType):
        return {key: _detach(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_detach(item) for item in value]
    return value


def _load():
    merged = {}
    directory = Path(__file__).with_name("data")
    for filename in _FILES:
        path = directory / filename
        shard = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(shard, dict) or set(merged) & set(shard):
            raise ValueError(f"Invalid or overlapping catalogue shard: {filename}")
        merged.update(shard)
    validate_catalogue(merged)
    return _freeze(merged)


_CATALOGUE = _load()


def packs(cid):
    """Return ten fully detached packs for a known career; unknown IDs raise."""
    if not isinstance(cid, str):
        raise KeyError(cid)
    return _detach(_CATALOGUE[cid])


def pack(cid, tier):
    """Return a detached pack at integer tier 1..10 (booleans are not tiers)."""
    if type(tier) is not int:
        raise TypeError("Specialism tier must be an integer")
    if not 1 <= tier <= 10:
        raise ValueError("Specialism tier must be between 1 and 10")
    if not isinstance(cid, str):
        raise KeyError(cid)
    return _detach(_CATALOGUE[cid][tier - 1])
