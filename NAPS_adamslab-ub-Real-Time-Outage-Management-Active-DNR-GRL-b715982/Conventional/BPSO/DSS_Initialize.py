"""
In this file the sectionalizing and tie switch details are specified. 
The DER details are also specified (in particular the ones with and without grid forming capability).
Also the path for the DSS file containing the circuit information is specified.
The final DSS circuit which will be used by the algorithm is created.
"""

import os
import networkx as nx
from  DSS_CircuitSetup import*

sectional_swt=[{'no':1,'line':'L19'},
               {'no':2,'line':'L24'},
               {'no':3,'line':'L26'},
               {'no':4,'line':'L43'},
               {'no':5,'line':'L58'},
               {'no':6,'line':'L67'},
               {'no':7,'line':'L81'},
               {'no':8,'line':'L86'},
               {'no':9,'line':'L101'},
               {'no':10,'line':'Sw2'},
               {'no':11,'line':'Sw3'},
               {'no':12,'line':'Sw4'},
               {'no':13,'line':'Sw5'}]


tie_swt=[{'no':1,'from node':'54','from conn':'.1.2.3', 'to node':'94','to conn':'.1.2.3', 'length':0.350,'code':'6', 'name':'Sw8'},
         {'no':2,'from node':'151','from conn':'.1.2.3', 'to node':'300','to conn':'.1.2.3', 'length':0.350,'code':'6', 'name':'Sw7'},
         {'no':3,'from node':'56','from conn':'.1.2.3', 'to node':'92','to conn':'.1.2.3', 'length':0.350,'code':'6', 'name':'L120'},
          {'no':4,'from node':'83','from conn':'.1.2.3', 'to node':'95','to conn':'.1.2.3', 'length':1.975,'code':'2', 'name':'L121'},
          {'no':5,'from node':'25','from conn':'.1.2.3', 'to node':'35','to conn':'.1.2.3', 'length':0.906,'code':'2', 'name':'L122'},
          {'no':6,'from node':'250','from conn':'.1.2.3', 'to node':'300','to conn':'.1.2.3', 'length':1.364,'code':'3', 'name':'L123'},
          {'no':7,'from node':'51','from conn':'.1.2.3', 'to node':'65','to conn':'.1.2.3', 'length':0.600,'code':'4', 'name':'L124'},
          {'no':8,'from node':'101','from conn':'.1.2.3', 'to node':'151','to conn':'.1.2.3', 'length':1.600,'code':'3', 'name':'L125'},
          {'no':9,'from node':'79','from conn':'.1.2.3', 'to node':'450','to conn':'.1.2.3', 'length':1.304,'code':'5', 'name':'L126'}]

generators=[{'no':1, 'bus': '39', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':2, 'bus': '46', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':3, 'bus': '71', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':4, 'bus': '75', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':5, 'bus': '79', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':6, 'bus': '96', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':7, 'bus': '108', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 250, 'kV': 4.16, 'Gridforming':'Yes'},
            {'no':8, 'bus': '11', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16, 'Gridforming':'No'},
            {'no':9, 'bus': '33', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16, 'Gridforming':'No'},
            {'no':10, 'bus': '56', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16, 'Gridforming':'No'},
            {'no':11, 'bus': '82', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16, 'Gridforming':'No'},
            {'no':12, 'bus': '91', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16,'Gridforming':'No'},
            {'no':13, 'bus': '104', 'numphase':3, 'phaseconn':'.1.2.3', 'size': 80, 'kV': 4.16 ,'Gridforming':'No'},
            ]
dispatch_loads = ['Load.s82a', 'Load.s84c', 'Load.s92c', 'Load.s88a', 'Load.s69a', 'Load.s100c', 'Load.s107b', 'Load.s109a', 'Load.s113a', 'Load.s48', 'Load.s49a', 'Load.s64b', 'Load.s66c', 'Load.s53a', 'Load.s11a', 'Load.s16c', 'Load.s20a', 'Load.s30c', 'Load.s22b']

n_actions = len(sectional_swt) + len(tie_swt) + len(dispatch_loads) # the switching actions and load shedding/pickup

substatn_id = '150'

# out_edges = ['Line.l13', 'Line.l51', 'Line.l65'] # SC1
# out_edges = [('13','18'), ('51','151'), ('65', '66')] # SC1

# out_edges=['Line.sw7','Line.l58','Line.l120', 'Line.l67', 'Line.l68'] #SC2
out_edges =[('151','300'), ('57','60'), ('56','92'), ('67','72'), ('67','97')]#SC2

def initialize():       
    FolderName = os.path.dirname(os.path.realpath(__file__))
    DSSfile = os.path.join(FolderName, "IEEE123Master.dss")
    DSSCktobj = CktModSetup(DSSfile,sectional_swt,tie_swt,generators) # initially the sectionalizing switches close and tie switches open
    DSSCktobj.dssSolution.Solve() #solving snapshot power flows
     
    if DSSCktobj.dssSolution.Converged:
       conv_flag = 1
    else:
       conv_flag = 0
    G_init=graph_struct(DSSCktobj)
    return DSSCktobj,G_init,conv_flag

DSSCktobj,G_init,conv_flag= initialize() 


def get_switch_status(DSSCktobj, switched_obj):
    """Return 1 for closed and 0 for open using the active line state.

    Some OpenDSS COM builds do not expose SwtControls.Action through pywin32.
    Reading the switched circuit element directly is more portable.
    """
    DSSCktobj.dssCircuit.SetActiveElement(switched_obj)
    element = DSSCktobj.dssCircuit.ActiveCktElement
    try:
        is_open = bool(element.IsOpen(1, 0))
    except Exception:
        is_open = False
        for phase in range(1, 4):
            try:
                is_open = is_open or bool(element.IsOpen(1, phase))
            except Exception:
                pass
    return 0 if is_open else 1

#--------- Graph with normal operating topology (with only sectionalizing switches)--for outage simulation (fault isolation)
tie_edges=[]
i=DSSCktobj.dssCircuit.SwtControls.First
while i>0:
    name=DSSCktobj.dssCircuit.SwtControls.Name
    if name[:5]=='swtie':
       line=DSSCktobj.dssCircuit.SwtControls.SwitchedObj
       br_obj=Branch(DSSCktobj,line)
       from_bus=br_obj.bus_fr.split('.')[0]
       to_bus=br_obj.bus_to.split('.')[0]
       tie_edges.append((from_bus,to_bus))
    i=DSSCktobj.dssCircuit.SwtControls.Next 
G_base = G_init.copy()    
G_base.remove_edges_from(tie_edges)

#---------------------Create a dictionary with name of generator element and corresponding buses and also one with blackstart capability---------------------------

Generator_Buses={} # list of dictionary create for opendss element extraction
Generator_BlackStart={}
i= DSSCktobj.dssCircuit.Generators.First
while i>0:
      elemName =  DSSCktobj.dssCircuit.ActiveCktElement.Name
      bus_connectn = DSSCktobj.dssCircuit.ActiveCktElement.BusNames[0].split('.')[0]
      # phases = DSSCktobj.dssCircuit.ActiveCktElement.NumPhases
      Generator_Buses[elemName]=bus_connectn
      num=int(elemName[-1])-1
      if generators[num]['Gridforming'] == 'Yes':
          Generator_BlackStart[elemName]=1
      else:
          Generator_BlackStart[elemName]=0 
      i = DSSCktobj.dssCircuit.Generators.Next

#----------------- Create a dictionary with the name of loads and corresponding bus ---------------------
Load_Buses={}
i= DSSCktobj.dssCircuit.Loads.First
while i>0:
      elemName =  DSSCktobj.dssCircuit.ActiveCktElement.Name
      bus_connectn = DSSCktobj.dssCircuit.ActiveCktElement.BusNames[0].split('.')[0]
      # phases = DSSCktobj.dssCircuit.ActiveCktElement.NumPhases
      Load_Buses[elemName]=bus_connectn
      i = DSSCktobj.dssCircuit.Loads.Next


#------------------ List of the network buses and bus connections -------------------------------------      
node_list=list(G_init.nodes())
edge_list=list(G_init.edges()) #the fixed set of edges
nodes_conn=[]
for bus in node_list:
    nodes_conn.append(Bus(DSSCktobj,bus).nodes)
    
#-----------For each bus creating a generator element, load element, blackstart indicator------------
# gen_buses = np.array(list(Generator_Buses.values())) # all the generator buses
# gen_elems=  list(Generator_Buses.keys()) # all the generator elements
# load_buses = np.array(list(Load_Buses.values())) #all the load buses
# load_elems = list(Load_Buses.keys()) #all the laod elements
# Bus_Info=[]

# for n in node_list:   
#     blackstart_flag=0
#     gen_names=[gen_elems[x]  for x in  np.where(gen_buses == n)[0]]
#     load_names=[load_elems[y]  for y in  np.where(load_buses == n)[0]]
#     if (len(gen_names)!=0) and (gen_names[-1].split('.')[0]=='Storage'): #if there is storage then it is blackstart DER
#        blackstart_flag=1
#     Bus_Info.append({'Bus_id':n, 'Load_names':load_names, 'Generator_names':gen_names, 'Black_start':blackstart_flag})   
#     # Use this information to encode the graph


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
    
    

#-----------End of simulation , now some code snippet for checking switches, voltages, currents
# Check switches status

AllSwitches=[]
i=DSSCktobj.dssCircuit.SwtControls.First
while i>0:
    name=DSSCktobj.dssCircuit.SwtControls.Name
    line=DSSCktobj.dssCircuit.SwtControls.SwitchedObj
    br_obj=Branch(DSSCktobj,line)
    from_bus=br_obj.bus_fr
    to_bus=br_obj.bus_to
    sw_status=get_switch_status(DSSCktobj, line)
    AllSwitches.append({'switch name':name,'edge name':line, 'from bus':from_bus.split('.')[0], 'to bus':to_bus.split('.')[0], 'status':sw_status})
    i=DSSCktobj.dssCircuit.SwtControls.Next    

SwitchLines=[(s['from bus'],s['to bus']) for s in AllSwitches]


# # Check Node Voltages
V_nodes=[]
for n in list(G_init.nodes()):
    V=Bus(DSSCktobj, n).Vmag
    temp_conn=Bus(DSSCktobj, n).nodes
    V_nodes.append({'name':n, 'Connection': temp_conn, 'Voltage':V})


# Check Line Currents
I_nodes=[]
for e in list(G_init.edges(data=True)):
    branchname=e[2]['label'][0]
    DSSCktobj.dssCircuit.SetActiveElement(branchname)
    I=DSSCktobj.dssCircuit.ActiveCktElement.Powers
    # I=Branch(DSSCktobj, branchname).Cap
    I_nodes.append({'name':branchname, 'Current':I})       
