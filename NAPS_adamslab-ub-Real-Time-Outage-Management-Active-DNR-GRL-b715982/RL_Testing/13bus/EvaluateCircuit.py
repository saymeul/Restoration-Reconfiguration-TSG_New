
"""
In this file the action is evaluated on the circuit to obtain result
PLease uncomment the required solution and outage scenario
"""
import os
import networkx as nx
from DSS_CircuitSetup import*

#------------------- User defined inputs to modify the standard test network ---------------------------------

sectional_swt=[{'no':1,'line':'632670'},
               {'no':2,'line':'671692'}]

tie_swt=[{'no':1,'from node':'646','from conn':'.2.3', 'to node':'684','to conn':'.1.3', 'length':2000,'code':'603'},
          {'no':2,'from node':'633','from conn':'.1.2.3','to node':'692','to conn':'.1.2.3','length':2000,'code':'601'}]

# Generic generators
#Jacobs, Nicholas, Shamina Hossain-McKenzie, and Adam Summers. "Modeling data flows with network calculus in cyber-physical systems: enabling feature analysis for anomaly detection applications." Information 12.6 (2021): 255.
generators=[{'no':1, 'bus':'645', 'numphase':1, 'phaseconn':'.2', 'size':20, 'kV':2.4, 'Gridforming':'No'},
            {'no':2, 'bus':'645', 'numphase':1, 'phaseconn':'.3', 'size':20, 'kV':2.4, 'Gridforming':'No'},
            {'no':3, 'bus':'634', 'numphase':3, 'phaseconn':'.1.2.3', 'size':1000, 'kV':0.48, 'Gridforming':'Yes'},
            {'no':4, 'bus':'684', 'numphase':1, 'phaseconn':'.1', 'size':50, 'kV':2.4, 'Gridforming':'No'},
            {'no':5, 'bus':'684', 'numphase':1, 'phaseconn':'.3', 'size':50, 'kV':2.4, 'Gridforming':'No'},
            {'no':6, 'bus':'680', 'numphase':3, 'phaseconn':'.1.2.3', 'size':1000, 'kV':4.16, 'Gridforming':'Yes'},
            {'no':7, 'bus':'675', 'numphase':3, 'phaseconn':'.1.2.3', 'size':500, 'kV':4.16,'Gridforming':'No'}]

substatn_id='sourcebus'

dispatch_loads = ['Load.671','Load.634a','Load.634b','Load.634c','Load.611','Load.652','Load.670b']


###########################################################################################################################################################################
##------ Test Scenario 1--------------------------------
Out_Lines = ['Line.670671'] #sc1


#------------- GCAPS Solution---------------
switchaction = [1, 1, 0, 1] 
Loadstatus = {'Load.671': 1,
  'Load.634a': 1,
  'Load.634b': 0,
  'Load.634c': 1,
  'Load.611': 0,
  'Load.652': 0,
  'Load.670b': 1} 

#--------- MLP Solution-----------------
# switchaction = [0, 0, 0, 1]  #sc1 MLP
# Loadstatus = {'Load.671': 1,
#   'Load.634a': 1,
#   'Load.634b': 1,
#   'Load.634c': 1,
#   'Load.611': 1,
#   'Load.652': 0,
#   'Load.670b': 1} #sc1 MLP

#-------MISOCP and BPSO solution--------------------
# switchaction = [1, 0, 1, 1] #sc1 MISOCP
# Loadstatus = {'671': 1, '634a': 1, '634b': 1, '634c': 1, '611': 1, '652': 1, '670b': 1} #sc1 MISOCP
###########################################################################################################################################################################



###########################################################################################################################################################################
##------ Test Scenario 2--------------------------------
# Out_Lines = ['Line.632670','Line.646684'] #sc2

#------------- GCAPS Solution---------------
# switchaction = [0, 1, 0, 1]  #sc2 GCAPS
# Loadstatus = {'Load.671': 1,
#   'Load.634a': 1,
#   'Load.634b': 0,
#   'Load.634c': 1,
#   'Load.611': 0,
#   'Load.652': 0,
#   'Load.670b': 1} #sc2 GCAPS

#--------- MLP Solution-----------------
# switchaction = [0, 0, 1, 1] #sc2 MLP
# Loadstatus = {'Load.671': 1,
#   'Load.634a': 0,
#   'Load.634b': 0,
#   'Load.634c': 0,
#   'Load.611': 0,
#   'Load.652': 0,
#   'Load.670b': 0} #sc2 MLP


#-------MISOCP and BPSO solution--------------------
# switchaction  = [0, 1, 0, 1] #sc2 MISOCP
# Loadstatus = {'Load.671': 1, 'Load.634a': 1, 'Load.634b': 1, 'Load.634c': 1, 'Load.611': 1, 'Load.652': 1, 'Load.670b': 1}
###########################################################################################################################################################################


# To get the details of switches and their status
def switchInfo(DSSCktobj):
    #Input:   DSS Circuit Object
    #Returns: A list of dictionaries which contains: 
    #         The name of the switch.
    #         The associated line of the switch (the edge label).
    #         The status of the switch in the DSS Circuit object

    AllSwitches = []
    i = DSSCktobj.dss.SwtControls.First()
    while i>0:
        name = DSSCktobj.dss.SwtControls.Name()
        line = DSSCktobj.dss.SwtControls.SwitchedObj()
        DSSCktobj.dss.Circuit.SetActiveElement(line)
        sw_status = DSSCktobj.dss.SwtControls.Action()-1
        AllSwitches.append({'switch name':name,'edge name':line, 'status':sw_status})
        i=DSSCktobj.dss.SwtControls.Next()

    return AllSwitches


#------------------- Creating a DSS Circuit Object ------------------------------ 
FolderName=os.path.dirname(os.path.realpath(__file__))
DSSfile=r""+ FolderName+ "/IEEE13Nodeckt.dss"
# DSSfile="IEEE13Nodeckt.dss"
DSSCktobj = CktModSetup(DSSfile,sectional_swt,tie_swt,generators) # initially the sectionalizing switches close and tie switches open

#-- Solve the circuit
DSSCktobj.dss.Solution.Solve() #solving snapshot power flows
if DSSCktobj.dss.Solution.Converged():
   conv_flag=1
else:
   conv_flag=0    
G_init=graph_struct(DSSCktobj)

##--- Getting generator Info
Generator_Buses={} # list of dictionary create for opendss element extraction
Generator_BlackStart={}
i= DSSCktobj.dss.Generators.First()
while i>0:      
      elemName = f'Generator.{DSSCktobj.dss.Generators.Name()}' # full element name with device type included
      DSSCktobj.dss.Circuit.SetActiveElement(elemName)
      bus_connectn = DSSCktobj.dss.CktElement.BusNames()[0].split('.')[0]
      # phases = DSSCktobj.dss.CktElement.NumPhases()
      Generator_Buses[elemName]=bus_connectn
      num=int(elemName[-1])-1
      if generators[num]['Gridforming'] == 'Yes':
          Generator_BlackStart[elemName]=1
      else:
          Generator_BlackStart[elemName]=0 
      i = DSSCktobj.dss.Generators.Next()

node_list=list(G_init.nodes())
#------ Assigning a black start indicator for generators--------------------------------
gen_buses = np.array(list(Generator_Buses.values())) # all the generator buses
gen_elems=  list(Generator_Buses.keys()) # all the generator elements
Gen_Info ={}
for n in node_list:
    blackstart_flag=0
    gen_names=[gen_elems[x]  for x in  np.where(gen_buses == n)[0]]
    if (len(gen_names)!=0):
        for g in gen_names:
            blackstart_flag = blackstart_flag + Generator_BlackStart[g] 
        Gen_Info[n]= {'Generators':gen_names, 'Blackstart':blackstart_flag}

#------- Implementing the scenario ------------------------------------------------------

#-- Remove the outage lines in Circuit
for branch in Out_Lines:
    # Remove the element from the DSSCktobj
    DSSCktobj.dss.Circuit.SetActiveElement(branch)
    DSSCktobj.dss.Text.Command(f'Open {branch} term=1')
    DSSCktobj.dss.Solution.Solve()      

#-- Remove the outage lines in Graph
for e in G_init.edges():
    edgename = G_init.edges[e]['label'][0]
    if edgename in Out_Lines:
        G_init.remove_edge(*e)

#-- Perform Line Switching in Circuit
switch_actionidx = 0
i=DSSCktobj.dss.SwtControls.First()
while (i>0):
    switch_actionidx= i-1
    if switchaction[switch_actionidx]==0: # if 0- open line
        DSSCktobj.dss.Text.Command('Swtcontrol.' + DSSCktobj.dss.SwtControls.Name() + '.Action=o')
        line=DSSCktobj.dss.SwtControls.SwitchedObj()
        b_obj=Branch(DSSCktobj, line)
        u=b_obj.bus_fr.split('.')[0]
        v=b_obj.bus_to.split('.')[0]
        if G_init.has_edge(u,v):
           G_init.remove_edge(u,v) # Remove the edge in graph domain
            
    else:
        DSSCktobj.dss.Text.Command('Swtcontrol.'+ DSSCktobj.dss.SwtControls.Name() + '.Action=c')
    i=DSSCktobj.dss.SwtControls.Next()

DSSCktobj.dss.Solution.Solve()

AllSwitches = switchInfo(DSSCktobj)

#-- Perform Load control
for load in Loadstatus:
    if Loadstatus[load] == 0:
       DSSCktobj.dss.Circuit.SetActiveElement('Load.'+ load)
       DSSCktobj.dss.Text.Command(load + '.enabled="False"')
    DSSCktobj.dss.Solution.Solve()
    
    
# Grid forming generator

# #----- Finding network components and find virtual slack ------#
Components= list(nx.connected_components(G_init)) #components formed due to outage
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
                       DSSCktobj.dss.Circuit.SetActiveElement(gen_name)
                       kva_val= kva_val + float(DSSCktobj.dss.Properties.Value('kVA'))
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

        DSSCktobj.dss.Circuit.SetActiveBus(Vs_locatn)
        # DSSCktobj.dssBus.kVBase gives the per phase (phase to neutral) voltage
        Vs_kv =DSSCktobj.dss.Bus.kVBase() * math.sqrt(3) # this has to be phase to phase
        DSSCktobj.dss.Text.Command(f"New Vsource.{Vs_name}  bus1={Vs_locatn}  basekV={str(Vs_kv)}  phases=3  Pu=1.02  angle=30  baseMVA={str(Vs_MVA)}  MVAsc3={str(Vs_MVAsc3)}  MVAsc1={str(Vs_MVAsc1)}  enabled=yes")
        # print(Vs_MVAsc3)
        # print(Vs_MVAsc1)
        # DSSCktobj.dssText.command = 'Formedit'+ ' Vsource.' +Vs_name
        for gens in Gen_Info[Vs_locatn]['Generators']:
            DSSCktobj.dss.Text.Command(gens + '.enabled=no')
DSSCktobj.dss.Solution.Solve()


V_nodes=[]
for b in DSSCktobj.dss.Circuit.AllBusNames():
    V=Bus(DSSCktobj, b).Vmag
    temp_conn=Bus(DSSCktobj, b).nodes
    V_nodes.append({'name':b, 'Connection': temp_conn, 'Voltage':V})  

DSSCktobj.dss.Transformers.First()
KVA_base=DSSCktobj.dss.Transformers.kVA() #To convert into per unit    
En_Supply=0
Total_Demand=0
for ld in list(DSSCktobj.dss.Loads.AllNames()): # For each load
    DSSCktobj.dss.Circuit.SetActiveElement(f"Load.{ld}") #set the load as the active element
    S=np.array(DSSCktobj.dss.CktElement.Powers()) # Power vector (3 phase P and Q for each load)
    ctidx = 2 * np.array(range(0, min(int(S.size/ 2), 3)))
    P = S[ctidx] #active power in KW
    Q = S[ctidx + 1] #reactive power in KVar
    
    Power_Supp = sum(P)
    
    Demand = float (DSSCktobj.dss.Properties.Value('kW'))  
    En_Supply = En_Supply + Power_Supp
    Total_Demand =  Total_Demand + Demand  

En_Supply_perc = En_Supply/Total_Demand

# Extracting the pu node voltages at all buses    
Vmagpu=[]
active_conn=[]
for b in node_list:    
    V = Bus(DSSCktobj,b).Vmag
    active_conn.append(Bus(DSSCktobj,b).nodes)
    temp_flag = np.isnan(V) # Nodes which are isolated with loads but no generators return nan-- ignore that(consider as inactive)
    if np.any(temp_flag,where=True):
        V[temp_flag] = 0
        temp_conn=[n for n in active_conn[node_list.index(b)] if temp_flag[n-1]==False] #the bus nodes active are only those with numerical(not nan)
        active_conn[node_list.index(b)]=np.array(temp_conn) #only active node connections
    Vmagpu.append(V)
    
Vmax=1.10
Vmin=0.90    
V_Viol= []

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
    
print('The Energy Supplied is:') 
print(En_Supply)

print('The Volatge violation:')
print(V_ViolSum)