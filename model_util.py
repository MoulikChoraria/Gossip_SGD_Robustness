import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import torch.optim as optim
import time
import os
from collections import OrderedDict
from torch.utils.data import Subset

def quantizer_topk(gradient, k = 5):
    absoulte = torch.abs( gradient )
    sign  = torch.sign(gradient)
    values,indices = torch.topk( absoulte, k , sorted = False ,dim=0)
    gradient.zero_()
    gradient.scatter_(0,indices,values)
    #transform gradient to torch
    return gradient*sign

def quantizer_lossy( gradient, k = 64 ):
    norm = torch.norm( gradient )
    absoulte = torch.abs( gradient )
    absoulte = ( absoulte/norm )*k
    floor = torch.floor(absoulte)
    random_ceil = torch.rand(*gradient.shape) < ( gradient - floor )
    floor = ( floor + random_ceil.float() ) * (1/k)
    #rescale
    return (norm) * ( torch.sign(gradient) * floor )

def ring( num_workers ):
    ring = torch.zeros([num_workers, num_workers])
    for i in range(num_workers-1):
        ring[i,i+1] = 1.0
        ring[i,i-1] = 1.0
    #close
    ring[num_workers - 1, 0 ] = 1.0
    ring[num_workers - 1, num_workers-2 ] = 1.0
    for i in range(num_workers):
        ring[i,i] = 1
    return ring

def torus(sqrt_num_workers):
    num_workers = sqrt_num_workers*sqrt_num_workers
    torus = networkx.generators.lattice.grid_2d_graph(sqrt_num_workers,sqrt_num_workers, periodic=True)
    torus = networkx.adjacency_matrix(torus).toarray()
    for i in range(num_workers):
        torus[i,i] = 1
    return torus

def degree_k( num_workers , k ):
    half_k = k/2
    W  = torch.zeros([num_workers, num_workers])
    for i in range(num_workers):
        
        count = 0
        column = i
        while count < half_k:
            count = count+1
            #left
            if i-count >= 0 :
                W[i, i-count]  = 1.0
            else :
                W[ i, num_workers + i - count ] = 1.0
            #right
            if i+count < num_workers:
                W[i, i+count]  = 1.0
            else:
                W[i, i+count - num_workers ] = 1.0				
    for i in range(num_workers):
        W[i,i] = 1
    return W

def trainset_node_split(dataset, N, seed = 0):
    np.random.seed(seed)
    a = np.arange(len(dataset))
    np.random.shuffle(a)
    datasets = {}
    size = int(len(dataset)/N)
    for i in range(N):
        datasets[i] = Subset(dataset, a[i*size:(i+1)*size].tolist())
    return datasets

def count_correct(outputs, labels,criterion):
    """ count correct predictions """

    if isinstance(criterion, nn.BCELoss):
        predicted = (outputs > 0.5).to(dtype=torch.int64)
        labels = (labels  > 0.5).to(dtype=torch.int64)
    elif isinstance(criterion, nn.CrossEntropyLoss):
        _, predicted = outputs.max(1)
    else:
        print('Error in criterion')
        raise ValueError

    correct = (predicted == labels).sum().item()

    return correct
