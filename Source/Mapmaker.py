import numpy as np
import healpy as hp
import math
import os
import sys
import matplotlib
import matplotlib.pyplot as plt
from Specifications import Specifications
from PrimaryBeams import PrimaryBeams
from VisibilitySimulator import VisibilitySimulator
import Geometry
from PointSourceCatalog import PointSourceCatalog
import MatricesForMapmaking as MapMats
from LoadVisibilities import LoadVisibilities
import scipy.constants as const
from GlobalSkyModel import GlobalSkyModel
plt.close('all')


def Mapmaker(mainDirectory, freq = 150, useLogFile = False, configFile = "configuration.txt",  **kwargs):
    """This function makes maps from visibilities and also calculates the associated map statistics. 
    
    Saves the results to binary (as pickles or numpy arryas) and returns the folder where they are located"""        
    
    #Load in everything we need, figure out which LSTs to work with
    print "Now working on mapmaking at " + str(freq) + " MHz..."             
    s = Specifications(mainDirectory, configFile,freq)
    s.OverrideSpecifications(kwargs)
    os.system("rm -rf " + s.resultsFolder)
    os.system("mkdir " + s.resultsFolder)
    if useLogFile: sys.stdout = open(s.resultsFolder + 'log.txt', 'w')    
    
    #Info related to time, geometry, primary beams, and point sources
    times = Geometry.Times(s)
    times.CutOutUnusedLSTsAndGroupIntoSnapshots(s)
    coords = Geometry.Coordinates(s)
    PBs = PrimaryBeams(s)
    ps = PointSourceCatalog(s,times)
    if s.useAdaptiveHEALPixForPSF: coords.convertToAdaptiveHEALPix(s, times)
    
    #Simulate or load visibilities
    if s.simulateVisibilitiesWithGSM or s.simulateVisibilitiesWithPointSources:
        visibilities = VisibilitySimulator(s,PBs,ps,times,coords)
    else:
        visibilities = LoadVisibilities(s,times)
    visibilities *= s.convertJyToKFactor
    
    #Prepare visibilities
    visibilities /= s.convertJyToKFactor #converts to temperature units
    Geometry.rephaseVisibilitiesToSnapshotCenter(s,visibilities,times)
    MapMats.inverseCovarianceWeightVisibilities(s,visibilities)
    
    #Perform mapmaking and calculate PSFs
    print "Now calculating map and map statistics..."    
    coaddedMap = np.zeros(coords.nFacetPixels)
    PSF = np.zeros((coords.nFacetPixels,coords.nPSFPixels))
    pointSourcePSF = np.zeros((coords.nFacetPixels, ps.nSources))
    for snapshot in times.snapshots:    
        print "Working on snapshot at LST = " + str(round(snapshot.centralLST,4)) + "..."
        NinvTimesy = MapMats.calculateNinvTimesy(visibilities, snapshot)
        Ninv = MapMats.calculateNInv(s,snapshot)
        KAtranspose = MapMats.calculateKAtranspose(s,snapshot,coords,PBs)    
        coaddedMap += 2 * np.real(np.dot(KAtranspose[coords.facetIndexLocationsInPSFIndexList,:], NinvTimesy))
        PSF += 2 * np.real(np.dot(KAtranspose[coords.facetIndexLocationsInPSFIndexList,:], np.dot(np.diag(Ninv), KAtranspose.conj().transpose())))    
        if s.PSFforPointSources and ps.nSources > 0:
            pointSourceAmatrix = MapMats.calculatePSAmatrix(s,snapshot,ps,PBs)
            pointSourcePSF += 2 * np.real(np.dot(KAtranspose[coords.facetIndexLocationsInPSFIndexList,:], np.dot(np.diag(Ninv), pointSourceAmatrix)))
            
    #Renormalize maps and PSFs and save results
    #Dmatrix = np.diag(np.diag(PSF[:,coords.facetIndexLocationsInPSFIndexList])**(-1)) #This is the version I used in Dillon et al. 2015. I think the D ~ I is more logical.
    Dmatrix = np.diag(np.ones((coords.nFacetPixels)) / PSF[coords.facetIndexOfFacetCenter,coords.PSFIndexOfFacetCenter])
    PSF = np.dot(Dmatrix,PSF)
    coaddedMap = np.dot(Dmatrix,coaddedMap)
    mapNoiseCovariance = np.dot(PSF[:,coords.facetIndexLocationsInPSFIndexList],np.transpose(Dmatrix))
    if s.PSFforPointSources and ps.nSources > 0: pointSourcePSF = np.dot(Dmatrix,pointSourcePSF)
    
    MapMats.saveAllResults(s,times,ps,Dmatrix,PSF,coaddedMap,pointSourcePSF)
    if useLogFile: sys.stdout = sys.__stdout__
    return s.resultsFolder
        

if __name__ == "__main__":
    mainDirectory = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0] #Directory above this one
    resultsDirectory = Mapmaker(mainDirectory)
    s, times, ps, Dmatrix, PSF, coaddedMap, pointSourcePSF = MapMats.loadAllResults(resultsDirectory)    
    coords = Geometry.Coordinates(s)
    if s.useAdaptiveHEALPixForPSF: coords.convertToAdaptiveHEALPix(s, times)    
    #plt.figure()
    #plt.scatter(coords.PSFRAs, coords.PSFDecs, c = np.log10(np.abs(PSF[coords.facetIndexOfFacetCenter,:])), s = 1024 / coords.newPSFNSIDEs)
    #plt.colorbar()
    #plt.show()
    