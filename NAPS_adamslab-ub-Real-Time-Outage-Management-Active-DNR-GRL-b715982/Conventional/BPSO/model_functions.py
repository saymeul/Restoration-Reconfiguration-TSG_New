"""

The fitness function, solution implementation, and penalty for constraints are also defined .

"""
from DSS_Initialize import*


# To get the details of switches and their status
def switchInfo(DSSCktobj):
    #Input:   DSS Circuit Object
    #Returns: A list of dictionaries which contains: 
    #         The name of the switch.
    #         The associated line of the switch (the edge label).
    #         The status of the switch in the DSS Circuit object
    
    AllSwitches = []
    i = DSSCktobj.dssCircuit.SwtControls.First
    while i>0:
        name = DSSCktobj.dssCircuit.SwtControls.Name
        line = DSSCktobj.dssCircuit.SwtControls.SwitchedObj
        sw_status = get_switch_status(DSSCktobj, line)
        AllSwitches.append({'switch name':name,'edge name':line, 'status':sw_status})        
        i=DSSCktobj.dssCircuit.SwtControls.Next

    return AllSwitches    

# Constraint for voltage violation 
def Volt_Constr(Vmagpu,active_conn):
    #Input: The pu magnitude of node voltages at all buses, node activated or node phase of all buses
    Vmax=1.10
    Vmin=0.90
    V_Viol  = []
    V_ViolSum=0
    for i in range(len(active_conn)):
        for phase_co in active_conn[i]:
            if (Vmagpu[i][phase_co-1]<Vmin):  
                viol = abs(Vmin-Vmagpu[i][phase_co-1])/Vmin
                V_Viol.append(viol)
            if (Vmagpu[i][phase_co-1]>Vmax): 
                viol = abs(Vmagpu[i][phase_co-1]-Vmax)/Vmax                   
                V_Viol.append(viol)
    if len(V_Viol)!=0:
        V_ViolSum = (np.sum(V_Viol))/(len(G_init.nodes())*3)
    else: 
        V_ViolSum = 0
    return V_ViolSum  

def simulate_action(position_vector, scenario_edges=None, attack_context=None, verbose=True):
     # Get Initial circuit 
     action = position_vector
     scenario_edges = list(out_edges if scenario_edges is None else scenario_edges)
     attack_context = attack_context or {}
     perceived_out_edges = list(scenario_edges) + list(attack_context.get("extra_out_edges", []))
     load_weights = attack_context.get("load_weights", {})

     DSSCktObj,G_init,conv_flag= initialize() # local DSS object for just implementing action
     G_sc=G_init.copy() # Copy to create graph scenario
     
    # -------------Implement Line Switching Action on DSSCircuit Object
     switch_actionidx = 0
     i=DSSCktObj.dssCircuit.SwtControls.First
     while (i>0):
         switch_actionidx= i-1
         if action[switch_actionidx]==0: # if 0- open line
             DSSCktObj.dssText.command=('Swtcontrol.' + DSSCktObj.dssCircuit.SwtControls.Name+ '.Action=o')
         else:
             DSSCktObj.dssText.command=('Swtcontrol.'+ DSSCktObj.dssCircuit.SwtControls.Name+ '.Action=c')
         i=DSSCktObj.dssCircuit.SwtControls.Next 
         
     DSSCktObj.dssSolution.Solve()     
 
    # -------------Implement Load Shedding Action on DSSCircuit Object
 
     for load_actionidx in range(switch_actionidx + 1, n_actions):
         loadname = dispatch_loads[load_actionidx-switch_actionidx-1] 
         if action[load_actionidx] == 0: # If load is shed- disable the load
            DSSCktObj.dssCircuit.SetActiveElement(loadname)
            DSSCktObj.dssText.command=(loadname + '.enabled="False"')
         DSSCktObj.dssSolution.Solve()    
             
         
    #----Disable outage lines from DSSCircuit and also from Graph Scenario
     for o_e in perceived_out_edges:
         (u,v)=o_e        
         if G_sc.has_edge(u,v):
             G_sc.remove_edge(u,v) # Remove the edge in graph domain
         branch_name= G_init.edges[o_e]['label']
         # Remove the element from the DSSCktobj
         DSSCktObj.dssCircuit.SetActiveElement(branch_name)
         DSSCktObj.dssText.command=(branch_name + '.enabled="False"')
     DSSCktObj.dssSolution.Solve()    
 
     #---------- Also remove the open switches from Graph Scenario
     i=DSSCktObj.dssCircuit.SwtControls.First
     while i>0:
           # name=DSSCktobj.dssCircuit.SwtControls.Name
           line=DSSCktObj.dssCircuit.SwtControls.SwitchedObj
           if get_switch_status(DSSCktObj, line) == 0:
              b_obj=Branch(DSSCktObj, line)
              u=b_obj.bus_fr.split('.')[0]
              v=b_obj.bus_to.split('.')[0]
              if G_sc.has_edge(u,v):
                 G_sc.remove_edge(u,v) # Remove the edge in graph domain
           i=DSSCktObj.dssCircuit.SwtControls.Next    
     
     # #----- Finding network components and find virtual slack ------#
     Components= list(nx.connected_components(G_sc)) #components formed due to outage
     Virtual_Slack=[] # for each component not connected to sourcebus...we will assign a slack 
     if len(Components) >1 : #Only if there exists a network component unconnected to sourcebus virtual slack is assigned
         for C in Components: #for each component        
             if substatn_id not in C: # for the component unconnected to sourcebus
                 Slack_DER={'name':'','kVA':0}
                 # Find the DER corresponding to slack bus (largest grid forming DER) in component     
                 for gen_bus, gen_info in Gen_Info.items():
                     if gen_bus in C and gen_info['Blackstart']==1: #if generator is present and has gridforming capability
                        kva_val=0
                        for gen_name in gen_info['Generators']: #get total KVA at node
                            DSSCktObj.dssCircuit.SetActiveElement(gen_name)
                            kva_val= kva_val + float(DSSCktObj.dssCircuit.ActiveCktElement.Properties('kVA').Val)
                        if kva_val > Slack_DER ['kVA'] : # if multiple grid forming DERs, largest grid forming DER is slack
                           Slack_DER['kVA'] = kva_val
                           Slack_DER['name']= ('bus_'+ gen_bus)
                 Virtual_Slack.append(Slack_DER)
     
     #---- Assign slack bus in DSSCkt at the buses with virtual slack in different graph components               
     for vs in Virtual_Slack:
         Vs_name=vs['name']
         if Vs_name != '':
             Vs_locatn=Vs_name.split('_')[1]
             Vs_MVA = Vs_MVAsc3 = vs['kVA']/1000 #MVA and MVAsc3 are set to be same
             Vs_MVAsc1 = Vs_MVAsc3/3 # MVAsc1 approax 1/3 of MVAsc3
             
             DSSCktObj.dssCircuit.SetActiveBus(Vs_locatn)
             # DSSCktobj.dssBus.kVBase gives the per phase (phase to neutral) voltage
             Vs_kv =DSSCktObj.dssBus.kVBase * math.sqrt(3) # this has to be phase to phase
             DSSCktObj.dssText.command=('New Vsource.'+ Vs_name + ' bus1=' + Vs_locatn + ' basekV=' + str(Vs_kv) +' phases=3 Pu=1.00 angle=30 baseMVA=' + str(Vs_MVA) + ' MVAsc3=' + str(Vs_MVAsc3) +' MVAsc1=' + str(Vs_MVAsc1) + ' enabled =yes')
             # print(Vs_MVAsc3)
             # print(Vs_MVAsc1)
             # DSSCktobj.dssText.command = 'Formedit'+ ' Vsource.' +Vs_name   
             for gens in Gen_Info[Vs_locatn]['Generators']:
                 DSSCktObj.dssText.command = (gens + '.enabled=no')             
     DSSCktObj.dssSolution.Solve()  
     if DSSCktObj.dssSolution.Converged:
        conv_flag = 1
     else:
        conv_flag = 0
      
     # Evaluating energy supplied
     DSSCktObj.dssTransformers.First
     KVA_base=DSSCktObj.dssTransformers.kva
 
     En_Supply=0
     Total_Demand=0
     Perceived_En_Supply=0
     Perceived_Total_Demand=0
     for ld in list(DSSCktObj.dssLoads.AllNames): # For each load
         load_elem = "Load." + ld
         DSSCktObj.dssCircuit.SetActiveElement(load_elem) #set the load as the active element
         S=np.array(DSSCktObj.dssCircuit.ActiveCktElement.Powers) # Power vector (3 phase P and Q for each load)
         ctidx = 2 * np.array(range(0, min(int(S.size/ 2), 3)))
         P = S[ctidx] #active power in KW
         Q = S[ctidx + 1] #reactive power in KVar
         Power_Supp = sum(P) # total active power supplied at load
         Demand = float (DSSCktObj.dssCircuit.ActiveCktElement.Properties('kw').Val)
         if np.isnan(Power_Supp):
             Power_Supp = 0    # Nodes which are isolated with loads but no generators return nan-- ignore that(consider as inactive)   
         En_Supply = En_Supply + Power_Supp
         Total_Demand =  Total_Demand + Demand  
         weight = float(load_weights.get(load_elem, load_weights.get(load_elem.lower(), 1.0)))
         Perceived_En_Supply = Perceived_En_Supply + weight * Power_Supp
         Perceived_Total_Demand = Perceived_Total_Demand + weight * Demand
         En_Supply_perc = Perceived_En_Supply/Perceived_Total_Demand if Perceived_Total_Demand else 0.0
         True_En_Supply_perc = En_Supply/Total_Demand if Total_Demand else 0.0
      
     # Extracting the pu node voltages at all buses
     
     Vmagpu=[]
     active_conn=[]
     for b in node_list:    
         V = Bus(DSSCktObj,b).Vmag
         active_conn.append(Bus(DSSCktObj,b).nodes)
         temp_flag = np.isnan(V) # Nodes which are isolated with loads but no generators return nan-- ignore that(consider as inactive)
         if np.any(temp_flag,where=True):
             V[temp_flag] = 0
             temp_conn=[n for n in active_conn[node_list.index(b)] if temp_flag[n-1]==False] #the bus nodes active are only those with numerical(not nan)
             active_conn[node_list.index(b)]=np.array(temp_conn) #only active node connections
         Vmagpu.append(V)    
     
     V_viol=Volt_Constr(Vmagpu,active_conn)
     
     if conv_flag ==1: 
         temp = En_Supply_perc - V_viol
         if np.isnan(temp) or np.isinf(temp):
            f = 0
         else:
            f = temp
         
     else:
         f = 0
        

     if verbose:
        print(f)
     loads_served = int(np.sum(action[len(sectional_swt) + len(tie_swt):]))
     loads_shed = len(dispatch_loads) - loads_served
     return {
        "fitness": float(f),
        "energy_kw": float(En_Supply),
        "total_demand_kw": float(Total_Demand),
        "energy_ratio": float(True_En_Supply_perc),
        "perceived_energy_ratio": float(En_Supply_perc),
        "voltage_violation": float(V_viol),
        "convergence_violation": 0.0 if conv_flag == 1 else 1.0,
        "loads_served": loads_served,
        "loads_shed": loads_shed,
     }


def objective_func(position_vector, scenario_edges=None, attack_context=None, verbose=True):
     return simulate_action(position_vector, scenario_edges=scenario_edges, attack_context=attack_context, verbose=verbose)["fitness"]

