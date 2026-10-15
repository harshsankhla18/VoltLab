"""Transparent first-order educational battery module model; not a safety certification."""
from math import exp

CHEMISTRIES = {
    'NMC': dict(voltage=3.7, capacity=3.0, resistance=0.035, mass=0.047, cost=4.2, max_current=6.0, max_voltage=4.2, min_voltage=3.0),
    'LFP': dict(voltage=3.2, capacity=3.2, resistance=0.025, mass=0.075, cost=3.7, max_current=6.4, max_voltage=3.65, min_voltage=2.5),
}

def simulate(config):
    chem = config.get('chemistry','NMC')
    if chem not in CHEMISTRIES: raise ValueError('Unsupported chemistry')
    c = CHEMISTRIES[chem]
    ns, np = int(config.get('series',4)), int(config.get('parallel',3))
    current = float(config.get('current',8))
    ambient = float(config.get('ambient',25))
    cooling = float(config.get('cooling',1.0))
    duration = float(config.get('duration',60))
    soc = float(config.get('soc',90))
    age = float(config.get('age',0))
    variation = float(config.get('variation',0))
    for valid, label in [(1<=ns<=24,'series must be 1..24'),(1<=np<=24,'parallel must be 1..24'),(0<=current<=200,'current must be 0..200 A'),(-10<=ambient<=60,'ambient must be -10..60 C'),(0.2<=cooling<=8,'cooling must be 0.2..8'),(1<=duration<=240,'duration must be 1..240 min'),(0<=soc<=100,'soc must be 0..100'),(0<=age<=100,'age must be 0..100%'),(0<=variation<=20,'variation must be 0..20%')]:
        if not valid: raise ValueError(label)
    count = ns*np
    capacity_factor = 1 - 0.002*age
    effective_capacity = c['capacity']*np*capacity_factor*(1-variation/200)
    voltage = ns*c['voltage']
    resistance = ns*c['resistance']/np*(1+0.005*age)
    loaded_voltage = max(0,voltage-current*resistance)
    nominal_energy = voltage*c['capacity']*np
    usable_energy = voltage*effective_capacity*soc/100*0.90
    heat = current**2*resistance
    mass = count*c['mass']*1.22 + 0.12 + 0.12*(cooling-0.2)
    cost = count*c['cost'] + 13 + 8*cooling + 2.5*ns
    volume_l = count*0.019*1.55 + 0.20 + 0.04*cooling
    # Lumped module model: Cth [J/K], UA [W/K]. Constant current and R.
    cth = max(1, mass*850)
    ua = 0.6 + 2.5*cooling
    tau = cth/ua
    max_time = duration*60
    steps = 60
    points = []
    for i in range(steps+1):
        t = max_time*i/steps
        temp = ambient + (heat/ua)*(1-exp(-t/tau))
        discharged_ah = current*t/3600
        state = max(0,soc-100*discharged_ah/max(effective_capacity,0.01))
        points.append({'minute':round(t/60,2),'temperature':round(temp,2),'soc':round(state,2),'voltage':round(loaded_voltage,2)})
    peak = points[-1]['temperature']
    cell_current = current/np
    warnings=[]
    if cell_current > c['max_current']: warnings.append('Cell discharge current exceeds example continuous-current assumption.')
    if peak > 45: warnings.append('Estimated temperature exceeds 45 C screening threshold.')
    if loaded_voltage/ns < c['min_voltage']: warnings.append('Estimated loaded cell voltage below minimum voltage threshold.')
    if current*duration/60 > effective_capacity*soc/100: warnings.append('Requested discharge exceeds available state-of-charge energy; trace is not load-cutoff truncated.')
    if variation>10: warnings.append('High cell variation: group-average model cannot predict weakest-cell behavior.')
    if cooling>3: warnings.append('Cooling beyond baseline may require active hardware, parasitic power, and additional cost.')
    if not warnings: warnings=['No screening thresholds exceeded in this simplified scenario; this does not establish physical safety.']
    return {'inputs':{'chemistry':chem,'series':ns,'parallel':np,'current':current,'ambient':ambient,'cooling':cooling,'duration':duration,'soc':soc,'age':age,'variation':variation},'metrics':{'cells':count,'nominalVoltage':round(voltage,2),'loadedVoltage':round(loaded_voltage,2),'capacityAh':round(effective_capacity,2),'nominalEnergyWh':round(nominal_energy,2),'usableEnergyWh':round(usable_energy,2),'resistanceOhm':round(resistance,4),'heatWatts':round(heat,2),'peakTempC':round(peak,2),'massKg':round(mass,2),'volumeL':round(volume_l,2),'costUsd':round(cost,2),'cellCurrentA':round(cell_current,2),'estimatedFullDischargeMinutes':round(effective_capacity*60/current,1) if current else None},'warnings':warnings,'trace':points,'assumptions':['Example chemistry parameters are illustrative placeholders, not manufacturer-certified datasheet values.','Cells in each group assumed identical except coarse capacity-variation derating.','Constant-current discharge, fixed nominal OCV, constant resistance and uniform module temperature.','Thermal capacitance approximated as module mass x 850 J/(kg K); cooling UA = 0.6 + 2.5 x cooling W/K.','Usable energy uses 90% fixed factor and starting SOC; does not model cutoff or dynamic voltage curve.','Costs, packaging and volume are illustrative estimates in USD.','No short-circuit, thermal runaway, detailed BMS, charging CC-CV, balancing or electrochemical ageing physics.']}

def compare(config):
    base=simulate(config)
    improved=simulate({**config,'cooling':min(8,float(config.get('cooling',1))*2)})
    parallel=simulate({**config,'parallel':min(24,int(config.get('parallel',3))+1)})
    designs=[{'name':'Baseline','result':base},{'name':'Enhanced cooling','result':improved},{'name':'Extra parallel string','result':parallel}]
    for d in designs:
        m=d['result']['metrics']
        hard_ok=m['peakTempC']<=45 and m['cellCurrentA']<=CHEMISTRIES[config.get('chemistry','NMC')]['max_current']
        d['feasible']=hard_ok
        d['score']=round(m['usableEnergyWh']/max(1,m['costUsd']) - max(0,m['peakTempC']-40)*2 - m['massKg']*0.4,2) if hard_ok else None
    feasible=[d for d in designs if d['feasible']]
    winner=max(feasible,key=lambda x:x['score'])['name'] if feasible else None
    return {'designs':designs,'recommended':winner,'recommendationBasis':'Screening feasibility: peak <=45 C and cell current <= illustrative chemistry limit; score = usable Wh / USD - 2*max(0,Tpeak-40) - 0.4*mass(kg). Scores are heuristic, not optimized physics.','limitations':'Only 3 candidates; illustrative cell data and first-order lumped model. Validate with datasheets and lab testing before any hardware build.'}


def optimize(config, constraints=None):
    """Enumerate small series/parallel designs and rank constraint-satisfying candidates.
    This is a transparent heuristic search over the illustrative model, not a certified optimizer.
    """
    constraints = constraints or {}
    target_energy = float(constraints.get('minEnergyWh', 120))
    max_temp = float(constraints.get('maxTempC', 45))
    max_cost = float(constraints.get('maxCostUsd', 100))
    max_mass = float(constraints.get('maxMassKg', 3.0))
    chemistry = config.get('chemistry', 'NMC')
    if chemistry not in CHEMISTRIES: raise ValueError('Unsupported chemistry')
    for ok, label in [(10 <= target_energy <= 10000, 'minimum energy must be 10..10000 Wh'), (20 <= max_temp <= 80, 'maximum temperature must be 20..80 C'), (1 <= max_cost <= 100000, 'maximum cost must be 1..100000 USD'), (0.1 <= max_mass <= 1000, 'maximum mass must be 0.1..1000 kg')]:
        if not ok: raise ValueError(label)
    candidates=[]
    # Explore a manageable grid, retaining the user's operating conditions.
    for ns in range(3, 13):
        for np in range(1, 13):
            candidate_config={**config, 'series':ns, 'parallel':np}
            result=simulate(candidate_config)
            m=result['metrics']
            chemistry_limits=CHEMISTRIES[chemistry]
            voltage_ok=(m['loadedVoltage']/ns) >= chemistry_limits['min_voltage']
            cell_current_ok=m['cellCurrentA'] <= chemistry_limits['max_current']
            thermal_ok=m['peakTempC'] <= max_temp
            energy_ok=m['nominalEnergyWh'] >= target_energy
            cost_ok=m['costUsd'] <= max_cost
            mass_ok=m['massKg'] <= max_mass
            feasible=all([voltage_ok,cell_current_ok,thermal_ok,energy_ok,cost_ok,mass_ok])
            # Weighted, normalized score: reward energy, penalize cost/mass/temperature.
            score=(0.42*min(m['nominalEnergyWh']/max(target_energy,1), 2.0)
                   +0.24*(1-min(m['costUsd']/max(max_cost,1),1))
                   +0.18*(1-min(m['massKg']/max(max_mass,0.1),1))
                   +0.16*(1-min(max(m['peakTempC']-config.get('ambient',25),0)/max(max_temp-config.get('ambient',25),1),1)))
            reasons=[]
            if energy_ok: reasons.append('meets minimum nominal energy')
            else: reasons.append('below minimum energy target')
            if thermal_ok: reasons.append('within selected temperature limit')
            else: reasons.append('exceeds selected temperature limit')
            if cost_ok: reasons.append('within cost budget')
            else: reasons.append('over cost budget')
            if mass_ok: reasons.append('within mass limit')
            else: reasons.append('over mass limit')
            if not cell_current_ok: reasons.append('cell current exceeds illustrative limit')
            if not voltage_ok: reasons.append('loaded cell voltage below illustrative minimum')
            candidates.append({'series':ns,'parallel':np,'label':f'{ns}S{np}P','feasible':feasible,'score':round(score*100,1),'metrics':m,'reasons':reasons,'config':candidate_config})
    feasible=sorted((x for x in candidates if x['feasible']),key=lambda x:(x['score'],x['metrics']['nominalEnergyWh']),reverse=True)
    ranked=feasible[:8] if feasible else sorted(candidates,key=lambda x:(x['score'],-x['metrics']['costUsd']),reverse=True)[:8]
    return {'constraints':{'minEnergyWh':target_energy,'maxTempC':max_temp,'maxCostUsd':max_cost,'maxMassKg':max_mass},
            'evaluated':len(candidates),'feasibleCount':len(feasible),'recommended':ranked[0] if feasible else None,
            'ranked':ranked,'status':'feasible' if feasible else 'no_feasible_design',
            'method':'Enumerated 120 configurations (3S–12S, 1P–12P). Hard filters enforce energy, temperature, cost, mass, illustrative cell-current and loaded-voltage limits. Remaining candidates are ranked using a transparent weighted heuristic.',
            'limitations':'Uses illustrative cell parameters and a first-order model. The score is a decision aid, not an optimality proof or safety certification. Validate datasheets and test data before engineering use.'}
