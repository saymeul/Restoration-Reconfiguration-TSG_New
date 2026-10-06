"""
Functions required for initializing the circuit.
The DSS circuit is set up along with the bus and branch objects.
The Graph model of the DSS Circuit is also instantiated here.

"""

import win32com.client
import numpy as np
import math
import networkx as nx


class DSS():  # to initialize the DSS circuit object and extract results
      
    def __init__(self,filename): 
        
        self.filename=filename
        self.dssObj=win32com.client.Dispatch("OpenDSSEngine.DSS") #deploying DSS Engine
        
        if self.dssObj.Start(0)==False:
           print ("Problem with OpenDSS Engine initialization")
           
        else: # redeclaring variables defined under DSS object
            self.dssText=self.dssObj.Text
            self.dssCircuit=self.dssObj.ActiveCircuit
            self.dssSolution=self.dssCircuit.Solution            
            self.dssTopology=self.dssCircuit.Topology
            self.dssBus = self.dssCircuit.ActiveBus
            self.dssCktElement=self.dssCircuit.ActiveCktElement
            self.dssLines=self.dssCircuit.Lines
            self.dssLoads=self.dssCircuit.Loads
            self.dssTransformers=self.dssCircuit.Transformers               
          
    def compile_ckt_dss(self): # Compiling the OpenDSS circuit
        self.dssObj.ClearAll()
        self.dssText.Command="compile [" + self.filename +"]" 
            
    def get_ckt_base(self):
        self.dssTransformers.First
        self.KVA_base=self.dssTransformers.kva
        self.KV_base=self.dssTransformers.kv
        self.Z_base=((self.KV_base**2)*1000)/self.KVA_base
        return(self.KVA_base,self.KV_base,self.Z_base)
  
    def get_AllBuses(self):
        return self.dssCircuit.AllBusNames
    
    def get_AllLines(self):
        return self.dssLines.AllNames    
       
    def get_AllTransformers(self):
        return self.dssTransformers.AllNames
    
    def get_BusLoads(self):
        self.Load_dict={}
        i=self.dssCircuit.FirstPCElement() #set first power conversion element active
        while i>0:
              elname=self.dssCktElement.Name
              if elname.split('.')[0]=='Load':
                  name=elname.split('.')[1]
                  bus=self.dssCktElement.Busnames[0].split('.')[0]
                  self.dssLoads.Name=name
                  P_load=self.dssLoads.kW
                  Q_load=self.dssLoads.kvar
                  NumPhases=self.dssCktElement.NumPhases    
                  NodeOrder=self.dssCktElement.NodeOrder
                  Nodes=[0,0,0]
                  for i in range(len(NodeOrder)):
                      if NodeOrder[i]!=0:
                          Nodes[NodeOrder[i]-1]=1

                  self.Load_dict[name]={'Bus':bus,'NumPhases':NumPhases, 'Nodes':Nodes, 'Pload':P_load,'Qload':Q_load}
              i=self.dssCircuit.NextPCElement()
        return(self.Load_dict)     
    
    def get_Sourcebus(self): #!! May have to change with PV and BESS
        self.sources=[]
        i=self.dssCircuit.Vsources.First
        while i>0:
              self.dssCircuit.SetActiveElement(self.dssCircuit.Vsources.Name)
              self.sources.append(self.dssCircuit.ActiveCktElement.BusNames[0].split('.')[0])
              i=self.dssCircuit.Vsources.Next
        return(self.sources)                                                       
    
    def get_Lines_RX(self, Lines, Z_base): #to get the line resistance and reactance matrix and length
        self.R_Line={} #dictionary of resistance of lines
        self.X_Line={} #dictionary of reactance of lines
        for h in Lines:
            self.dssCircuit.SetActiveElement('Line.'+ h)

            Rmat_final=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            Xmat_final=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]        
            Rmat_l=self.dssLines.Rmatrix #extract Rmatrix of line (in ohms/length; tuple format)
            Xmat_l=self.dssLines.Xmatrix #extract Xmatrix of line (in ohms/length; tuple format)        
            len_line=self.dssLines.Length #extract length of line  #Rmatrix and Xmatrix will be by default converted to same unit of length by DSS
            Rmat=[(len_line*j)/Z_base for j in Rmat_l] #list format; in ohms*length/base ---in pu
            Xmat=[(len_line*k)/Z_base for k in Xmat_l] #list format; in ohms*length/base ---in pu
            Num_phases=self.dssCktElement.NumPhases
            node_seq=self.dssCktElement.NodeOrder
            node_seq=node_seq[0:Num_phases]        
        
            # assigning values to corresponding phases
            if Num_phases==3:
                Rmat_final[0][:]=Rmat[0:3]
                Rmat_final[1][:]=Rmat[3:6]
                Rmat_final[2][:]=Rmat[6:9]
               
                Xmat_final[0][:]=Xmat[0:3]
                Xmat_final[1][:]=Xmat[3:6]
                Xmat_final[2][:]=Xmat[6:9]
           
            if Num_phases==2:
                (p,q)=node_seq
                Rmat_final[p-1][p-1]=Rmat[0]
                Rmat_final[p-1][q-1]=Rmat[1]
                Rmat_final[q-1][p-1]=Rmat[2]
                Rmat_final[q-1][q-1]=Rmat[3]
                
                Xmat_final[p-1][p-1]=Xmat[0]
                Xmat_final[p-1][q-1]=Xmat[1]
                Xmat_final[q-1][p-1]=Xmat[2]
                Xmat_final[q-1][q-1]=Xmat[3]
            
            if Num_phases==1:
                (p,)=node_seq
                Rmat_final[p-1][p-1]=Rmat[0]
                Xmat_final[p-1][p-1]=Xmat[0]
                
            self.R_Line['Line.'+h] = np.array(Rmat_final)
            self.X_Line['Line.'+h] = np.array(Xmat_final)
        return(self.R_Line, self.X_Line)
 
    
    def get_Transformers_RX(self, Transformers, Z_base): #to get the transformer resistance  and reactance and length
        self.R_Trans={}
        self.X_Trans={}
        for t in Transformers:
            self.dssCircuit.SetActiveElement('Transformer.'+ t)

            Rmat_final=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            Xmat_final=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]             
            Num_phases=self.dssCktElement.NumPhases
            node_seq=self.dssCktElement.NodeOrder
            node_seq=list(node_seq[0:Num_phases])
            for n in node_seq: #for phase a
                Rmat_final[n-1][n-1]=0.01/Z_base
                Xmat_final[n-1][n-1]=0.01/Z_base
      
            self.R_Trans['Transformer.'+ t] = np.array(Rmat_final)
            self.X_Trans['Transformer.'+ t] = np.array(Xmat_final)
        return(self.R_Trans, self.X_Trans)     
    
    
# Bus class contains the bus object details
class Bus:
    def __init__(self,DSSCktobj,bus_name):
        """
        Inputs:
            circuit object
            bus name
        Contains:
            Vmag-  pu voltage magnitude at bus nodes (3 phase)
            Vang-  pu voltage angle at bus nodes (3 phase)
            nodes- node connection at bus
            Vmax- max pu voltage at bus
            Vmin- min pu voltage at bus
        """ 
        Vmag=np.zeros(3)
        Vang=np.zeros(3)
        DSSCktobj.dssCircuit.SetActiveBus(bus_name)
        V=DSSCktobj.dssBus.puVmagAngle # pair of magnitude and angle of voltages in pu
        nodes=np.array(DSSCktobj.dssBus.Nodes) #Node connection
        for indx in range(len(nodes)):
            Vmag[nodes[indx]-1]=V[int(indx*2)] #assigning the voltages acc to node connection
            Vang[nodes[indx]-1]=V[int(indx*2)+1]
        # Vmin=min(v for v in Vmag if v > 0)
        # Vmax=max(Vmag)
        self.Vmag = Vmag # 3 phase pu voltage at the buses
        self.Vang = Vang
        self.nodes=nodes
        # self.Vmax=Vmax
        # self.Vmin=Vmin    

        
class Branch:  # to extract properties of branch
    def __init__(self,DSSCktobj,branch_fullname):
        """
        Inputs:
            circuit object
            branch name
        Contains:                
            bus_fr - from bus name
            bus_to - to bus name  
            nodes- nodal connections
            nphases - number of phases
            Cap - average current flow            
        """
        
        # Calculating base current
        DSSCktobj.dssTransformers.First
        KVA_base=DSSCktobj.dssTransformers.kva # S base
        KV_base=DSSCktobj.dssTransformers.kv #L-L V base
        I_base=KVA_base/(math.sqrt(3)*KV_base)
                
        DSSCktobj.dssCircuit.SetActiveElement(branch_fullname)
        
        bus_connections=DSSCktobj.dssCktElement.BusNames
        bus1= bus_connections[0]
        bus2= bus_connections[1]   
                
        i=np.array(DSSCktobj.dssCktElement.CurrentsMagAng)
        ctidx = 2 * np.array(range(0, min(int(i.size/ 4), 3)))
        I_mag = i[ctidx] #branch current in A
        I_ang=i[ctidx + 1] #angle in deg
        nphases=DSSCktobj.dssCktElement.NumPhases
        nodes=DSSCktobj.dssCktElement.NodeOrder
        # MaxCap=DSSCktobj.dssCktElement.EmergAmps
        MaxCap=DSSCktobj.dssCktElement.NormalAmps
        Isqmax= (MaxCap/I_base) * (MaxCap/I_base) # maximum capacity square in pu 
       # https://sourceforge.net/p/electricdss/discussion/861976/thread/8aa13830/
       # Problem is that Line.650632 already exceeds normal amps in Opendss=400 A and 
       # Normal Amps in Kerstings book =530 A. So I will consider EmergAmps=600 A
        #I_avg=np.average(I_mag)/I_base #average of all three phases in pu
        self.bus_fr=bus1
        self.bus_to=bus2
        self.nphases=nphases
        self.nodes=nodes
        self.Isqmax=Isqmax
        #self.Cap=I_avg
        #self.MaxCap=MaxCap         
        
        
def CktModSetup(DSSfile,sectional_swt,tie_swt,generators): # give DERs as input
    DSSCktobj= DSS(DSSfile) #create a circuit object
    DSSCktobj.compile_ckt_dss() #compiling the circuit #compiling should only be done once in the beginning
    #Setting the iteration limits higher and disabling the warning message window
    DSSCktobj.dssText.command = "Set Maxiterations=5000" 
    DSSCktobj.dssText.command = "Set maxcontroliter=5000"
    # Donot put control mode= OFF at all...it will not allow switch control
    DSSCktobj.AllowForms=False  

    #### Make switch additions #####
    
    for sline in sectional_swt:  # the sectionalizing switch control is established (the normal state is closed)
        DSSCktobj.dssText.command=('New swtcontrol.swSec'+ str(sline['no']) +' SwitchedObj=Line.'+ sline['line'] +' Normal=c SwitchedTerm=1 Action=c') #normally close      
    
    for tline in tie_swt: # First create new lines corresponding to tie lines
        if tline['name']=='Sw7' or tline['name']=='Sw8':        
               DSSCktobj.dssText.command=('New Line.'+ tline['name'] + ' Bus1=' + tline['from node']+ tline['from conn']  + ' Bus2=' + tline['to node'] +tline['to conn'] + '  r1=1e-3 r0=1e-3  x1=0.000 x0=0.000 c1=0.000 c0=0.000 Length=0.001')
        else:    
            DSSCktobj.dssText.command=('New Line.'+ tline['name'] + ' Bus1=' + tline['from node']+ tline['from conn']  + ' Bus2=' + tline['to node'] +tline['to conn'] + ' LineCode=' + tline['code'] + ' Length=' + str(tline['length']))
        DSSCktobj.dssText.command=('New swtcontrol.swTie'+ str(tline['no']) +' SwitchedObj=Line.'+ tline['name'] + ' Normal=o SwitchedTerm=1 Action=o') #normally open  
        # Swobj='Line.'+ tline['from node'] + tline['to node']
        # DSSCktobj.dssCircuit.SetActiveElement(Swobj)
        # DSSCktobj.dssCircuit.ActiveCktElement.Open(1,0)
        # DSSCktobj.dssText.command='open ' + Swobj +' term=1'       #switching the line open
    # For switches if Normal State= 1 it is open and if Normal State= 2  it is close in DSS
    
    
    ## Make DER additions #####  
    
    ##---------------- Generator Object ----------------------------------------
    for gen in generators:
        # connection - default is wye (Y/LN)
        # https://sourceforge.net/p/electricdss/discussion/861976/thread/f81830f0/
        DSSCktobj.dssText.command=('New Generator.G' + str(gen['no']) + ' bus1=' + gen['bus'] + gen['phaseconn'] + ' Phases=' + str(gen['numphase']) + ' Kv=' + str(gen['kV']) + ' Kw=' + str(gen['size']) + ' Pf=0.8 Model=1')        
    
    # ##---------------- Time series simulation (Load shapes)-------------------------------- 
    DSSCktobj.dssText.command='redirect Loadshapes.dss' # load multiplication factor
    # # PV profile already added when defining PV
    DSSCktobj.dssText.command='BatchEdit Load..* Daily=loadshape_multload' # To add the same loadshape to all loads    
    
    return DSSCktobj
        

# ---------Graph formation and Adjacency matrix--------------# In this directional graph with multiple edges is considered
def graph_struct(DSSCktobj):       
    #Getting all elements
    All_Elems=[]
    i=DSSCktobj.dssCircuit.PDElements.First
    while i>0:
          All_Elems.append(DSSCktobj.dssCircuit.PDElements.Name)
          i=DSSCktobj.dssCircuit.PDElements.Next

    G_original=nx.MultiDiGraph() #Multigraph to contain parallel branches between nodes
    for e in All_Elems:
        if ((e.split('.')[0]=='Line') or (e.split('.')[0]=='Transformer')): #only if its a line or transformer used in graph(capacitors avoided)
            branch_obj=Branch(DSSCktobj,e) #creating  a branch object instance with full name
            sr_node=branch_obj.bus_fr.split('.')[0] #extracting source bus of branch
            tar_node=branch_obj.bus_to.split('.')[0] #extracting target bus of branch
            name=e
            DSSCktobj.dssCircuit.SetActiveElement(e)
            # if (not(DSSCktobj.dssCircuit.ActiveCktElement.IsOpen(1,0))): #if the line is closed only add to graph
            G_original.add_edge(sr_node, tar_node, label=name)
    return G_original


def graph_nodir(DSSCktobj): # This is unidirectional and single edge graph used for circuit evaluation
    G_original=nx.Graph()
    i=DSSCktobj.dssCircuit.PDElements.First #Getting all power delivery elements
    while i>0:
          label_edge=[]
          e=DSSCktobj.dssCircuit.PDElements.Name
          if ((e.split('.')[0]=='Line') or (e.split('.')[0]=='Transformer')): #only if its a line or transformer used in graph(capacitors avoided)
             branch_obj=Branch(DSSCktobj,e) #creating  a branch object instance with full name
             sr_node=branch_obj.bus_fr.split('.')[0] #extracting source bus of branch
             tar_node=branch_obj.bus_to.split('.')[0] #extracting target bus of branch
             name=e
             if (G_original.has_edge(sr_node,tar_node)):#if it already has an edge just add the new element name to existing label.
                label_edge=[x  for x in G_original.edges[sr_node,tar_node]['label']]
                label_edge.append(name)
                G_original.edges[sr_node,tar_node]['label']=label_edge

             elif (G_original.has_edge(tar_node,sr_node)):
                  label_edge=[x for x in G_original.edges[tar_node,sr_node]['label']]
                  label_edge.append(name)
                  G_original.edges[tar_node,sr_node]['label']= label_edge

             else:
                 label_edge.append(name)
                 G_original.add_edge(sr_node, tar_node, label= label_edge)

          i=DSSCktobj.dssCircuit.PDElements.Next

    return G_original