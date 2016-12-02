import numpy as np 
from gr import GetGR 
import copy

def g_lnprob(p , lpf , temp, lpfargs): 
        
    L = lpf(p , *lpfargs ) 
    
    if (np.isfinite(L) ):
        bias = g_getbias( L , temp )
    else:
        bias = 0
      
    return (L + bias, bias)
    
    
    
def g_getbias( L , temp ):
     
    
    return L * temp
    
def initiate_pool(i):
    pass


class Umbrella:
    
    def __init__(self,lpf,temp, ic, nows, sampler=None, comm=None, ranks=None, lpfargs=[], samplerargs={}   ):
        
        self.lpf = lpf
        self.lpfargs = lpfargs
        self.temp = temp
        self.tempfac = 1.0 / temp - 1.0 
        self.nows = nows
        
        # Initialize the positions around the ic  
        self.ic = np.array(ic).squeeze()
        if (self.ic.ndim==1):
            self.p = (1e-3) * np.random.normal(size=(nows, len(ic) ) ) + self.ic 
        else:
            self.p = self.ic
        
        self.lnprob0 = None  
        self.blobs0 = None  
        
        self.traj_pos = []
        self.traj_prob = []
        self.traj_blob = []
        
        self.tsteps = 0
        self.acorval = 0
        
        self.pool = None
            
        if not comm==None:
            from mpi4py import MPI 
            import mpi_pool

            if MPI.COMM_WORLD.Get_rank() in ranks:
                self.pool = mpi_pool.MPIPool( comm=comm )
                self.pool.map( initiate_pool , range(  self.pool.size ) )
                 

        # Setup the sampler. At the moment, just use emcee with g_lnprob as the log likelihood eval
        self.sampler = sampler(self.nows,  np.shape(self.p)[1] , g_lnprob, pool=self.pool , args=[self.lpf , self.tempfac, lpfargs ], **samplerargs )
         
    
    def getbias(self, L ):
        
        # return the log(bias) function.
        
        return g_getbias( L , self.tempfac )
    
    def get_state(self):
        
        return [self.p , self.lnprob0, self.blobs0]
    
    def set_state(self,z):
          
        p,lnprob0,blobs0 = z
        
        self.p = np.copy( np.array(p) )
        self.lnprob0 = np.copy( np.array( lnprob0 ) )
        self.blobs0 = np.copy( np.array( blobs0 ) )
        
        return
    
    def get_traj(self):
        
        return [self.traj_pos , self.traj_prob, self.traj_blob]
    
    def get_acor(self):
        
        return self.acorval
    
    def set_traj(self,z):
          
        traj_pos,traj_prob,traj_blob = z
        
        self.traj_pos = copy.deepcopy( traj_pos )
        self.traj_prob = copy.deepcopy( traj_prob ) 
        self.traj_blob = copy.deepcopy( traj_blob )
        
        return
    
 
    def sample(self, nsteps):
                
        # Now just run the sampler.
        # If you wanted to swap out your own code, this is the place to do it.
        
        for (pos , prob , rstate , blobs ) in  self.sampler.sample( self.p , lnprob0=self.lnprob0 , blobs0=self.blobs0, iterations=nsteps ):
            
            self.traj_pos.append( pos.copy() )
            self.traj_prob.append( prob.reshape(np.shape(blobs)) - blobs  )
            self.traj_blob.append( np.array(blobs).copy() )
         
        self.p = pos
        self.lnprob0 = prob
        self.blobs0 = blobs
        self.tsteps += nsteps 
        
        self.gr =  GetGR( np.array(self.traj_pos ) )
        
        try:
            self.acorval = np.max( self.sampler.acor )
        except:
            self.acorval = self.tsteps
        
        
        
        
        
        