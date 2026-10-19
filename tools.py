"""Engineering tools the agent can call. Each returns a JSON-serialisable dict."""
import ast, json, math, operator
from pathlib import Path

MATERIALS = json.loads((Path(__file__).parent / "materials.json").read_text())
REPORT_DIR = Path("reports")

def _find(name: str):
    q = name.lower().strip()
    for key, m in MATERIALS.items():
        if q in key.lower() or any(q == a or a in q for a in m["aliases"]):
            return key, m
    raise ValueError(f"Unknown material '{name}'. Available: {list(MATERIALS)}")

def get_material_properties(name):
    key, m = _find(name)
    return {"material": key, **{k: v for k, v in m.items() if k != "aliases"},
            "note": "Typical handbook values (approximate) - verify against test data."}

def stress_concentration_hole(hole_dia_mm, plate_width_mm):
    r = hole_dia_mm / plate_width_mm
    if not 0 < r < 0.7:
        raise ValueError("d/w must be between 0 and 0.7")
    kt = 3.0 - 3.14 * r + 3.667 * r**2 - 1.527 * r**3  # Peterson, gross-section basis
    return {"d_over_w": round(r, 3), "Kt_gross": round(kt, 3), "Kt_net": round(kt * (1 - r), 3),
            "source": "Peterson, central circular hole in finite-width plate under tension"}

def fatigue_notch_factor(Kt, notch_radius_mm, material):
    _, m = _find(material)
    a = 0.0254 * (2070 / m["Su_MPa"]) ** 1.8          # Neuber constant, mm (Shigley)
    q = 1 / (1 + a / notch_radius_mm)
    return {"q": round(q, 3), "Kf": round(1 + q * (Kt - 1), 3), "neuber_a_mm": round(a, 4)}

_SURF = {"ground": (1.58, -0.085), "machined": (4.51, -0.265),
         "hot-rolled": (57.7, -0.718), "as-forged": (272.0, -0.995)}
_REL = {50: 1.0, 90: 0.897, 95: 0.868, 99: 0.814, 99.9: 0.753}
_LOAD = {"bending": 1.0, "axial": 0.85, "torsion": 0.59}

def marin_endurance_limit(material, surface="machined", diameter_mm=10, loading="bending", reliability_pct=99):
    _, m = _find(material)
    a, b = _SURF[surface]
    ka = min(a * m["Su_MPa"] ** b, 1.0)
    kb = 1.0 if loading == "axial" else (1.24 * diameter_mm ** -0.107 if diameter_mm >= 2.79 else 1.0)
    kc, kd = _LOAD[loading], _REL[reliability_pct]
    se = m["Se_prime_MPa"] * ka * kb * kc * kd
    return {"ka": round(ka, 3), "kb": round(kb, 3), "kc": kc, "kd": kd, "Se_MPa": round(se, 1)}

def goodman_safety_factor(sigma_a, sigma_m, Se, Su, Sy):
    n_f = 1 / (sigma_a / Se + sigma_m / Su)
    n_y = Sy / (sigma_a + sigma_m)  # Langer first-cycle yield check
    return {"n_fatigue_goodman": round(n_f, 3), "n_yield_langer": round(n_y, 3),
            "governing": "fatigue" if n_f < n_y else "yielding", "safe": min(n_f, n_y) >= 1}

def basquin_life(sigma_a, sigma_m, material, Kf=1.0, Se=None):
    _, m = _find(material)
    sa = Kf * sigma_a
    sa_eq = sa / (1 - sigma_m / m["sigma_f_MPa"])      # Morrow mean-stress correction
    if Se and sa_eq <= Se:
        return {"sigma_a_eq_MPa": round(sa_eq, 1), "life_cycles": "infinite", "reason": "below endurance limit"}
    n = 0.5 * (sa_eq / m["sigma_f_MPa"]) ** (1 / m["b"])
    return {"sigma_a_eq_MPa": round(sa_eq, 1), "life_cycles": float(f"{n:.3e}"),
            "method": "Basquin + Morrow mean-stress correction"}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}
_FUNCS = {"sqrt": math.sqrt, "log": math.log, "log10": math.log10, "sin": math.sin, "cos": math.cos,
          "tan": math.tan, "radians": math.radians, "pi": math.pi, "abs": abs}

def _ev(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_ev(n.left), _ev(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_ev(n.operand))
    if isinstance(n, ast.Name) and n.id in _FUNCS: return _FUNCS[n.id]
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
        return _FUNCS[n.func.id](*[_ev(a) for a in n.args])
    raise ValueError("Unsupported expression")

def calculator(expression):
    return {"expression": expression, "result": _ev(ast.parse(expression, mode="eval").body)}

def save_report(filename, markdown):
    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / (Path(filename).stem + ".md")
    path.write_text(markdown, encoding="utf-8")
    return {"saved_to": str(path)}

def _s(props, req, desc):
    return {"description": desc, "input_schema": {"type": "object", "properties": props, "required": req}}
_n, _t = {"type": "number"}, {"type": "string"}

TOOLS = [
    {"name": "get_material_properties", **_s({"name": _t}, ["name"], "Look up E, Sy, Su, Se', Basquin constants for a material.")},
    {"name": "stress_concentration_hole", **_s({"hole_dia_mm": _n, "plate_width_mm": _n}, ["hole_dia_mm", "plate_width_mm"], "Kt for a central hole in a plate under tension.")},
    {"name": "fatigue_notch_factor", **_s({"Kt": _n, "notch_radius_mm": _n, "material": _t}, ["Kt", "notch_radius_mm", "material"], "Convert Kt to fatigue notch factor Kf using notch sensitivity.")},
    {"name": "marin_endurance_limit", **_s({"material": _t, "surface": {"type": "string", "enum": list(_SURF)}, "diameter_mm": _n,
        "loading": {"type": "string", "enum": list(_LOAD)}, "reliability_pct": {"type": "number", "enum": list(_REL)}}, ["material"],
        "Corrected endurance limit Se using Marin factors (surface, size, load, reliability).")},
    {"name": "goodman_safety_factor", **_s({k: _n for k in ["sigma_a", "sigma_m", "Se", "Su", "Sy"]}, ["sigma_a", "sigma_m", "Se", "Su", "Sy"], "Goodman fatigue and Langer yield safety factors (MPa).")},
    {"name": "basquin_life", **_s({"sigma_a": _n, "sigma_m": _n, "material": _t, "Kf": _n, "Se": _n}, ["sigma_a", "sigma_m", "material"], "Cycles to failure via Basquin with Morrow mean-stress correction.")},
    {"name": "calculator", **_s({"expression": _t}, ["expression"], "Safely evaluate an arithmetic expression (sqrt, log, sin, pi...).")},
    {"name": "save_report", **_s({"filename": _t, "markdown": _t}, ["filename", "markdown"], "Save the final design-check report as a markdown file.")},
]
DISPATCH = {t["name"]: globals()[t["name"]] for t in TOOLS}

def execute_tool(name, args):
    try:
        return json.dumps(DISPATCH[name](**args))
    except Exception as e:  # surfaced to the agent so it can self-correct
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
