"""
In this file the sectionalizing and tie switch details are specified. 
The DER details are also specified (in particular the ones with and without grid forming capability). 
Also the path for the DSS file containing the circuit information is specified.
The final DSS circuit which will be used by the MISOCP is created.
"""
from DSS_CircuitSetup import *
import os
from math import sqrt
import numpy as np

#------------------- User defined inputs to modify the standard test network ---------------------------------
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

# Generic generators
#Jacobs, Nicholas, Shamina Hossain-McKenzie, and Adam Summers. "Modeling data flows with network calculus in cyber-physical systems: enabling feature analysis for anomaly detection applications." Information 12.6 (2021): 255.
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
# if 3 phase DSSCktobj.dss.Bus.kVBase()*math.sqrt(3)[KVLL] else DSSCktobj.dss.Bus.kVBase()[KVphase]
 
substatn_id = '150'

dispatch_loads = ['Load.s82a','Load.s84c', 'Load.s92c', 'Load.s88a', 'Load.s69a', 'Load.s100c', 'Load.s107b', 'Load.s109a', 'Load.s113a', 'Load.s48', 'Load.s49a', 'Load.s64b', 'Load.s66c', 'Load.s53a', 'Load.s11a', 'Load.s16c', 'Load.s20a', 'Load.s30c', 'Load.s22b']


#---------------Creating a DSS Circuit Object------------------------------ 
FolderName=os.path.dirname(os.path.realpath(__file__))
DSSfile=os.path.join(FolderName, "IEEE123Master.dss")

# We can also set all the loads to a new value and evaluate the circuit.
# In case we are doing this ensure the load dict is also modified
DSSCktobj=CktModSetup(DSSfile,sectional_swt,tie_swt,generators)

# Solve the Circuit
DSSCktobj.dssSolution.Solve()
if DSSCktobj.dssSolution.Converged:
    print("The Circuit solved successfully")
else:
    print('Circuit not solved')
    
#--------------- Extracting circuit Info------------------------------ 
CktLines=list(DSSCktobj.get_AllLines()) #All Lines (both closed and open)
CktTransformers=list(DSSCktobj.get_AllTransformers())#Transformers
CktBuses=DSSCktobj.get_AllBuses() #Buses
CktLoadDict=DSSCktobj.get_BusLoads() #Dictionary of Loads, connections, P and Q



# Getting Circuit Base
KVA_base,KV_base,Z_base=DSSCktobj.get_ckt_base()
  
# Creating a graph with DSS object to extract topological data     
DSSGraph=graph_struct(DSSCktobj)

CktElems_Connec={}
for e in list(DSSGraph.edges(data=True)):
    # busfrom=e[0], busto=e[1], elem=e[2]['label']
    CktElems_Connec[e[2]['label']]=(e[0],e[1])  
CktElems=list(CktElems_Connec.keys())


# Removing parallel edges between pair of buses
CktElems_mod=[]
CktElems_Connec_mod={}
for e in CktElems:
    if CktElems_Connec[e] not in list(CktElems_Connec_mod.values()):
        CktElems_mod.append(e)
        CktElems_Connec_mod[e]= CktElems_Connec[e]

#------Extracting and Assigning source information------------------------------ 
Sources= DSSCktobj.get_Sourcebus() #name of sources... we can add more

Source_Elems={} #To get the power delivery element incident on the sourcebus
for s in Sources:
    [(u,v)]=list(DSSGraph.edges(s))
    Source_Elems[s]=list(DSSGraph.get_edge_data(u,v).values())[0]['label']

Source_Cap={} # The capacity of power 
# To get source capacity run DSS at multiplication factor and get the power delivered by source
# CktPower=-1*DSSCktobj.dssCircuit.TotalPower[0]
# Source_Cap['150']=10*(CktPower/KVA_base) # (in pu) manually setting the sourcebus capacity to total power delivered 
Source_Cap[substatn_id]= 1000 #randomly setting at a very high value
Source_U={} #To set the voltage at sourcebus as 1.04 (slack)
for s in Sources:
    Source_U[s]=1.04 #(in pu)
   
    
#-------------------Extracting Load informations------------------------------
CktLoads=list(CktLoadDict.keys())

# # Dispatchable loads
DispLoads = []
for d in dispatch_loads:
    DispLoads.append(d.split('.')[1])
    

# Modifying the active and reactive power of loads CktLoadDict 
# Conversion to pu.
for ld in CktLoads:
    CktLoadDict[ld]['Pload'] = CktLoadDict[ld]['Pload']/KVA_base
    CktLoadDict[ld]['Qload'] = CktLoadDict[ld]['Qload']/KVA_base
    
# Extracting the loads connected to each bus
CktBusLoads={}
for b in CktBuses:
    loads=[]
    for ld in CktLoads:
        if CktLoadDict[ld]['Bus'] == b:
            loads.append(ld)
            CktBusLoads[b]=loads
            
# Extracting the capacity of Loads
LoadDemand={}
for ld in CktLoads:
    Pval=CktLoadDict[ld]['Pload']
    Qval=CktLoadDict[ld]['Qload']
    LoadDemand[ld]=[Pval,Qval]

        
#---------Extracting Lines with switches------------------------------
# To get switches
Switches=[]
i=DSSCktobj.dssCircuit.Swtcontrols.First
while i>0:
      name=DSSCktobj.dssCircuit.Swtcontrols.SwitchedObj.split('.')[1]
      line='Line.'+name
      Switches.append(line)
      i=DSSCktobj.dssCircuit.Swtcontrols.Next
      
# To find switchable elements
Elem_Switchable={}
for elem in CktElems:
    if elem in Switches:
        Elem_Switchable[elem]=1
    else:
        Elem_Switchable[elem]=0
        
#------------Computing the maximum current capacity square in pu
Elem_Isqmax={}
for elem in CktElems:
    branch_obj=Branch(DSSCktobj,elem)
    Elem_Isqmax[elem] =branch_obj.Isqmax

#-------------------Extracting Generator informations------------------------------
Phases=['a','b','c']
Generator_Dict={}

i = DSSCktobj.dssCircuit.Generators.First
while i>0:
    phase_connec=[]
    elemName =  DSSCktobj.dssCircuit.ActiveCktElement.Name
    bus_connectn = DSSCktobj.dssCircuit.ActiveCktElement.BusNames[0].split('.')[0]
    node_order = DSSCktobj.dssCircuit.ActiveCktElement.NodeOrder
    num_phases = DSSCktobj.dssCircuit.ActiveCktElement.NumPhases
    kw= (DSSCktobj.dssCircuit.Generators.kW)/KVA_base
    kvar=(DSSCktobj.dssCircuit.Generators.KVar)/KVA_base
    for n in range(num_phases):
        phase_connec.append(Phases[node_order[n]-1])    
    Generator_Dict[('Gen_'+str(i))]={'Bus':bus_connectn,'Phases':phase_connec,'Capacity_P':kw,'Capacity_Q':kvar, 'BlackStart':generators[i-1]['Gridforming']}    
    i = DSSCktobj.dssCircuit.Generators.Next

# Divide the Generators based on the type
Gridfeeding = Generator_Dict.copy()
Gridforming = Generator_Dict.copy()
for k in Generator_Dict:
    if Generator_Dict[k]['BlackStart']=='Yes':
        del Gridfeeding[k]
    else:
        del Gridforming[k]

# Generator Bus dictionary
GenBus_dict = {}
for b in CktBuses:
    GenBus_dict[b] = []
    
# Grid feeding added to generator buses while the grid forming is slack
for k in Gridfeeding:
    b = Generator_Dict[k]['Bus']
    GenBus_dict[b].append(k)

# Adding the gridforming DERs to sources since these are slack buses    
for k in Gridforming:
    sbus=Generator_Dict[k]['Bus']
    Source_Cap[sbus]=Gridforming[k]['Capacity_P']
    Source_U[sbus]=1.04
    s_elemlist = list(DSSGraph.out_edges(sbus,data=True))
    if len(s_elemlist)!=0:
       selem=s_elemlist[0][2]['label']
    else:
        selemlist=list(DSSGraph.in_edges(sbus,data=True))
        selem=selemlist[0][2]['label']
    Source_Elems[sbus]=selem
    Sources.append(sbus)    

# #------ Extracting the nodal connection for buses -----
BusNodeConnec={}
for b in CktBuses:
    busobj=Bus(DSSCktobj,b)
    nodes=[0,0,0]
    for n in busobj.nodes:
        nodes[n-1]=1
    BusNodeConnec[b]=nodes


#--------Extracting the nodal connection of lines------
ElemNodeConnec={}
for elem in CktElems:
    branch_obj=Branch(DSSCktobj,elem)
    No_phases=branch_obj.nphases
    Node_connec=branch_obj.nodes
    nodes=[0,0,0]
    for h in range(No_phases):
        nodes[Node_connec[h]-1]=1        
    ElemNodeConnec[elem]=nodes
    
  
#---------Extracting the immediate adjacent elements
Elem_AdjElems={}
for e in DSSGraph.edges(data=True):
    curr_elem=e[2]['label']
    nextElems=[]
    (u,v)=(e[0],e[1])
    for nex in DSSGraph.out_edges(v,data=True):
        nextElems.append(nex[2]['label'])
    # In a radial structure every node will have only 1 parent
    for nex in DSSGraph.in_edges(v,data=True): # This is considered to account for edges incident on 2nd vertex (although direction is considered in Graph(and there will be no incident edge other than current edge in radial netw) it is considered only using directionality variable in Powerflow )
        if (nex[2]['label']) != curr_elem:
            nextElems.append(nex[2]['label'])
    Elem_AdjElems[curr_elem]=nextElems
 


#-----------Extracting the Resistance and Reactance of all lines and transformers
R_Line, X_Line = DSSCktobj.get_Lines_RX(CktLines, Z_base)
R_Trans, X_Trans = DSSCktobj.get_Transformers_RX(CktTransformers, Z_base)


#-----------Combining Line and Transformer to create a dictionary of resistance and reactance for all elements
R_Elem={}
X_Elem={}
for elem in CktElems:
    el_type= elem.split('.')[0]
    if el_type== 'Line':
        R_Elem[elem]=R_Line[elem]
        X_Elem[elem]=X_Line[elem]
    if el_type== 'Transformer':
        R_Elem[elem]=R_Trans[elem]
        X_Elem[elem]=X_Trans[elem]        
    
       
#-----------Computing the modified Resistance and Reactance of all elements
Rmod_Elem={}
Xmod_Elem={}
Zmod_Elem={}
# alpha matrix
a1 = complex(-0.5, -sqrt(3)/2)
a2 = complex(-0.5, sqrt(3)/2)
a = np.array([[1, a1, a2], [a2, 1, a1], [a1, a2, 1]]) 
for elem in CktElems:  
    Zmod_Elem[elem]=[[0, 0, 0],[0, 0, 0],[0, 0, 0]]
    
    el_type= elem.split('.')[0]
    if el_type== 'Line':
        matR_real = a * R_Line[elem]
        matR_imag = a * X_Line[elem]
        Rmod= matR_real.real -matR_imag.imag        
               
        matX_real = a * X_Line[elem]
        matX_imag = a * R_Line[elem]
        Xmod = matX_real.real + matX_imag.imag
        
        for p in range(3):
            for q in range(3):
                Zmod_Elem[elem][p][q]=sqrt((R_Line[elem][p][q] * R_Line[elem][p][q]) + (X_Line[elem][p][q] * X_Line[elem][p][q]))
        
    if el_type== 'Transformer':
        matR_real = a * R_Trans[elem]
        matR_imag = a * X_Trans[elem]
        Rmod = matR_real.real -matR_imag.imag        
               
        matX_real = a * X_Trans[elem]
        matX_imag = a * R_Trans[elem]
        Xmod = matX_real.real + matX_imag.imag
        
        for p in range(3):
            for q in range(3):
                Zmod_Elem[elem][p][q]=sqrt((R_Trans[elem][p][q] * R_Trans[elem][p][q]) + (X_Trans[elem][p][q] * X_Trans[elem][p][q]))
    
    Rmod_Elem[elem]=Rmod.tolist()
    Xmod_Elem[elem]=Xmod.tolist()    

#------------Computing the maximum current capacity square in pu
Elem_Isqmax={}
for elem in CktElems:
    branch_obj=Branch(DSSCktobj,elem)
    Elem_Isqmax[elem] =branch_obj.Isqmax
  
        
#--------------Computing the voltage drop
def Vdrop_eqn(element, phase, prev_bus, VsqBus, PElem, QElem, IsqElem, Rmod_Elem, Xmod_Elem, Zmod_Elem):
    Phases=['a','b','c']
    Vdrop=0
    
    # Preceeding Bus Voltage
    V_prev= VsqBus[phase, prev_bus] 
    
    # Rmod_Elem * PElem
    V_rp= 0
    for h in range(3):
        V_rp= V_rp +  Rmod_Elem[element][Phases.index(phase)][h] * PElem[phase, element]
    # Xmod_Elem * QElem
    V_xq=0
    for h in range(3):
        V_xq= V_xq +  Xmod_Elem[element][Phases.index(phase)][h] * QElem[phase, element]
    
    # Zmod_elem * IsqElem
    V_zi=0
    for h in range(3):
        V_zi= V_zi +  Zmod_Elem[element][Phases.index(phase)][h] * IsqElem[phase, element]
    
    Vdrop= V_prev -2 *(V_rp + V_xq) + V_zi
    
    return Vdrop


""" For case with generators """ 

#### Modify by adding generators and load
#-----------Function defining Active Power Balance for each Element -------------
def P_balance(element, phase, PLoad, PElem, PSource, CktElems_Connec, ElemNodeConnec, CktBusLoads, CktLoadDict, Elem_AdjElems, Sources, Source_Elems, IsqElem, R_Elem, GenBus_dict, Generator_Dict, PGen):
    Phases=['a','b','c']
    P_balance=0 #(Power direction: entering is negative, leaving is negative)

#---- Power injection at Load connected to the to bus of element at phase
    to_bus=CktElems_Connec[element][1]
    if to_bus in CktBusLoads: #If the to bus has a load connected to it
        for load in CktBusLoads[to_bus]: #For each load connected to the bus
            if CktLoadDict[load]['Nodes'][Phases.index(phase)]==1: #If the phase considered is an active load phase
              P_balance= P_balance + (PLoad[load]/CktLoadDict[load]['NumPhases']) #The load is not assigned phases in OPF formulation so total power of load divide by phases

#---- Power flow along Lines adjacent to the element with considered phase
    if len(Elem_AdjElems[element])!=0: #If this line has adjacent lines
        for nexelem in Elem_AdjElems[element]: #For each adjacent line 
            if ElemNodeConnec[nexelem][Phases.index(phase)]==1: #If the adjacent line has the considered phase
                if CktElems_Connec[nexelem][0]== to_bus: #If the adjacent elem is succeeding elem , i.e., the from bus of adj elem is the to bus of considered elem
                    P_balance= P_balance + PElem[phase, nexelem]
                else: #If the adjacent elem is the preceeding elem i.e, the to bus of adj elem is the to bus of considered elem
                    P_balance= P_balance - PElem[phase, nexelem]
                
#---- Power flow if element is connected to substation
    if to_bus in Sources: #This is used if buses other than 'sourcebus' are assigned as sources
        P_balance= P_balance - PSource[phase, to_bus] #Power generation at to bus of elem with the phase
    
    if element == Source_Elems[Sources[0]]: #if the element is the network header element
        P_balance= P_balance - PSource[phase, Sources[0]]

#--- Powerflow if element is connected to Generator
    if len(GenBus_dict[to_bus])!=0: # if the to-bus has a generator
       for gen in GenBus_dict[to_bus]: # for each generator connected to the bus
           if phase in Generator_Dict[gen]['Phases']: #if the phase is active for the Generator
              P_balance = P_balance - PGen[phase, gen]
              
#---- Active Power loss
    P_loss=0
    for h in range(3):
        P_loss= P_loss +  R_Elem[element][Phases.index(phase)][h] * IsqElem[phase, element]
    
    P_balance= P_balance + P_loss
    return P_balance

#### Modify by adding generators and load
#-----------Function defining Reactive Power Balance for each Element -------------
def Q_balance(element, phase, QLoad, QElem, QSource, CktElems_Connec, ElemNodeConnec, CktBusLoads, CktLoadDict, Elem_AdjElems, Sources, Source_Elems, IsqElem, X_Elem, GenBus_dict, Generator_Dict, QGen):
    Phases=['a','b','c']
    Q_balance=0 #(Power direction: entering is negative, leaving is negative)

#---- Power injection at Load connected to the to bus of element at phase
    to_bus=CktElems_Connec[element][1]
    if to_bus in CktBusLoads: #If the to bus has a load connected to it
        for load in CktBusLoads[to_bus]: #For each load connected to the bus
            if CktLoadDict[load]['Nodes'][Phases.index(phase)]==1: #If the phase considered matches load phase
              Q_balance= Q_balance + (QLoad[load]/CktLoadDict[load]['NumPhases'])

#---- Power flow along Lines adjacent to the element with considered phase
    if len(Elem_AdjElems[element])!=0: #If this line has adjacent lines
        for nexelem in Elem_AdjElems[element]: #For each adjacent line 
            if ElemNodeConnec[nexelem][Phases.index(phase)]==1: #If the adjacent line has the considered phase
                if CktElems_Connec[nexelem][0]== to_bus: #If the adjacent elem is succeeding elem , i.e., the from bus of adj elem is the to bus of considered elem
                    Q_balance= Q_balance + QElem[phase, nexelem]
                else: #If the adjacent elem is the preceeding elem i.e, the to bus of adj elem is the to bus of considered elem
                    Q_balance= Q_balance - QElem[phase, nexelem]
                
#---- Power flow if element is connected to substation
    if to_bus in Sources: #This is used if buses other than 'sourcebus' are assigned as sources
        Q_balance= Q_balance - QSource[phase, to_bus] #Power generation at to bus of elem with the phase
    
    if element == Source_Elems[Sources[0]]: #if the element is the network header element
        Q_balance= Q_balance - QSource[phase, Sources[0]]

#--- Powerflow if element is connected to Generator
    if len(GenBus_dict[to_bus])!=0: # if the to-bus has a generator
       for gen in GenBus_dict[to_bus]: # for each generator connected to the bus
           if phase in Generator_Dict[gen]['Phases']: #if the phase is active for the Generator
              Q_balance = Q_balance - QGen[phase, gen]       
#---- Reactive Power loss
    Q_loss=0
    for h in range(3):
        Q_loss= Q_loss +  X_Elem[element][Phases.index(phase)][h] * IsqElem[phase, element]
    
    Q_balance= Q_balance + Q_loss    
    return Q_balance    

#--- SOC constraint LHS
def SOC_LHS(element, phase, prev_bus, IsqElem, VsqBus):
    return (IsqElem[phase, element] * VsqBus[phase, prev_bus])
        
def SOC_RHS(element, phase, PElem, QElem):   
    S_sq= (PElem[phase, elem] * PElem[phase, elem]) + (QElem[phase, elem] * QElem[phase, elem]) 
    return S_sq

#----Directionality according flow for each bus
def flowdefine(bus,ElemsFlow,DSSGraph,CktElems_mod): 
    directionality=0
    # DSSGraph is  a Directional multigraph
    for suc_bus in DSSGraph.neighbors(bus): #get suceeding nodes(buses)
        if DSSGraph.has_edge(bus,suc_bus): #if the edge exists
            elem=list(DSSGraph.get_edge_data(bus, suc_bus).values())[0]['label']
            if elem in CktElems_mod:
              directionality= directionality + ElemsFlow[elem,'i2']

    for prev_bus in DSSGraph.predecessors(bus): #  get previous or preceeding nodes(or bus)
        if DSSGraph.has_edge(prev_bus,bus): #if the edge exists
            elem= list(DSSGraph.get_edge_data(prev_bus, bus).values())[0]['label']
            if elem in CktElems_mod:
                directionality= directionality + ElemsFlow[elem,'i1']
               
    return directionality           
 
