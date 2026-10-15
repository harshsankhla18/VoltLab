from model import simulate,compare

def test_energy_scales_with_parallel():
    a=simulate({'parallel':2}); b=simulate({'parallel':4})
    assert b['metrics']['nominalEnergyWh']==2*a['metrics']['nominalEnergyWh']

def test_more_cooling_reduces_temperature():
    a=simulate({'cooling':1}); b=simulate({'cooling':3})
    assert b['metrics']['peakTempC']<a['metrics']['peakTempC']

def test_more_parallel_reduces_heat_at_fixed_current():
    a=simulate({'parallel':2}); b=simulate({'parallel':4})
    assert b['metrics']['heatWatts']<a['metrics']['heatWatts']

def test_compare_three():
    assert len(compare({'series':4,'parallel':3})['designs'])==3

def test_bad_input():
    try: simulate({'series':0})
    except ValueError: pass
    else: assert False
