import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from tools import *

def test_material_lookup(): assert get_material_properties("4140")["Su_MPa"] == 1020
def test_kt_hole(): assert abs(stress_concentration_hole(10, 100)["Kt_gross"] - 2.73) < 0.05
def test_kf_between_1_and_kt():
    kf = fatigue_notch_factor(2.7, 5, "1045")["Kf"]; assert 1 <= kf <= 2.7
def test_marin(): assert 0 < marin_endurance_limit("1045", "machined", 20)["Se_MPa"] < 315
def test_goodman(): assert goodman_safety_factor(100, 50, 200, 600, 500)["n_fatigue_goodman"] == 1.714
def test_basquin_infinite(): assert basquin_life(50, 0, "1045", Se=200)["life_cycles"] == "infinite"
def test_basquin_finite(): assert basquin_life(500, 0, "1045")["life_cycles"] < 1e6
def test_calc(): assert calculator("sqrt(16)+2**3")["result"] == 12
def test_calc_blocks_code():
    assert "error" in json.loads(execute_tool("calculator", {"expression": "__import__('os')"}))
def test_bad_material(): assert "error" in json.loads(execute_tool("get_material_properties", {"name": "unobtainium"}))
