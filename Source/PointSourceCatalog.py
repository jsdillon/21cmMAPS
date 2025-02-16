# SUPPORTING CLASS FOR JOINT MAPMAKING AND POWER SPECTRUM PIPELINE
# by Josh Dillon

import numpy as np
import healpy as hp
import math
import Geometry
import time
from PrimaryBeams import PrimaryBeams

class PointSourceCatalog:
    def __init__(self,s,times):
        #Compute GSM from 3 principal components appropriately weighted        
        try: 
            PBs = PrimaryBeams(s, freq=s.pointSourceReferenceFreq)            
            self.freq = s.freq
            self.catalog = np.loadtxt(s.pointSourceCatalogFilename)
            self.catalog = self.catalog[self.catalog[:,2] > .5*s.pointSourceBeamWeightedFluxLimitAtReferenceFreq, :] #assumes that the beam has a max value of 1, with an extra factor of 2 buffer
            
            # Determines if the beam-weighted flux of each point source is above the limit and deletes it from the catalog if it isn't
            middleLSTindex = int(math.floor(len(times.LSTs)/2.0))
            psAlts, psAzs = Geometry.convertEquatorialToHorizontal(s, self.catalog[:,0] * 2*np.pi/360, self.catalog[:,1] * 2*np.pi/360, times.LSTs[middleLSTindex])
            primaryBeamWeightsAtReferenceFreq = hp.get_interp_val(PBs.beamSquared("X","x",s.pointings[middleLSTindex]), np.pi/2-psAlts, psAzs)
            beamWeightedFluxesAtReferenceFreq = primaryBeamWeightsAtReferenceFreq * self.catalog[:,2]
            self.catalog = self.catalog[beamWeightedFluxesAtReferenceFreq > s.pointSourceBeamWeightedFluxLimitAtReferenceFreq, :]
            
            #Convert into a more useful format        
            self.RAs = self.catalog[:,0] * 2*np.pi/360
            self.decs = self.catalog[:,1] * 2*np.pi/360
            self.fluxes = self.catalog[:,2] 
            self.spectralIndices = self.catalog[:,3]    
            self.scaledFluxes = self.fluxes * (s.freq / s.pointSourceReferenceFreq)**(-self.spectralIndices)
            self.nSources = len(self.fluxes)
        except:
            self.nSources = 0
        
        print str(len(self.catalog)) + " point sources identified for specific modeling."